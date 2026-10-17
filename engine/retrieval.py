import hashlib
import json
import math
import re
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from engine.db import (
    get_cached_embedding,
    sanitize_fts_query,
    save_cached_embedding,
    search_products_fts,
)
from engine.guardrails import extract_amounts, script_of

PRONOUN_OR_SHORT_TOKENS = {
    "it", "this", "that", "these", "those", "they", "them", "same", "one",
    "ye", "yeh", "wo", "woh", "iska", "iski", "iske", "uska", "uski", "uske",
    "ha", "he", "te", "ti", "to", "hya", "tya",
}


@dataclass
class Context:
    shop: dict[str, Any]
    catalogue_block: str
    policies_block: str
    examples: list[dict[str, str]]
    known_amounts: set[int]
    retrieval_mode: str = "fts5_bm25"
    retrieved_products: list[Any] = field(default_factory=list)


STOCK_STATUS_MAP = {
    "in_stock": "in stock",
    "low_stock": "low stock (limited)",
    "out_of_stock": "out of stock",
    "made_to_order": "made to order",
}

# In-memory cache for product embeddings: (seller_id, product_id, text_hash) -> vector
_EMBEDDING_CACHE: dict[tuple[int, int, str], list[float]] = {}


def get_local_embedding(
    text: str,
    model: str = "nomic-embed-text",
    host: str = "http://localhost:11434",
    timeout: float = 1.5,
) -> list[float] | None:
    """Query local Ollama embeddings API with a tight 1.5s timeout.

    Fails gracefully returning None if Ollama is not running or model is missing.
    """
    if not text or not text.strip():
        return None

    url = f"{host.rstrip('/')}/api/embeddings"
    payload = json.dumps({"model": model, "prompt": text.strip()}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("embedding")
    except Exception:
        return None
    return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two float vectors using math.sqrt."""
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def reciprocal_rank_fusion(
    fts_ids: list[int],
    vector_ids: list[int],
    k: int = 60,
) -> list[int]:
    """Combine FTS5 and vector rankings using Reciprocal Rank Fusion (RRF)."""
    scores: dict[int, float] = {}

    for rank, doc_id in enumerate(fts_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    for rank, doc_id in enumerate(vector_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    return sorted(scores.keys(), key=lambda d: scores[d], reverse=True)


def _format_product_line(
    p: sqlite3.Row,
    variant_rows: list[sqlite3.Row],
    known_amounts: set[int],
) -> str:
    """Format a single product row with variants and attributes into a prompt string."""
    for v in variant_rows:
        known_amounts.add(int(v["price_inr"]))

    var_strs = [f"{v['label']} ₹{v['price_inr']}" for v in variant_rows]
    variants_summary = "; ".join(var_strs) if var_strs else "Price unavailable"

    cat_str = f" ({p['category']})" if p["category"] else ""

    attrs_str = ""
    if p["attributes"]:
        try:
            attrs_dict = json.loads(p["attributes"])
            attr_parts = []
            for k, val in attrs_dict.items():
                if isinstance(val, list):
                    attr_parts.append(f"{k}: {', '.join(str(x) for x in val)}")
                else:
                    attr_parts.append(f"{k}: {val}")
            if attr_parts:
                attrs_str = " | " + " | ".join(attr_parts)
        except json.JSONDecodeError:
            pass

    stock_text = STOCK_STATUS_MAP.get(p["stock_status"], p["stock_status"])
    line = f"- [{p['sku']}] {p['name']}{cat_str}: {variants_summary}{attrs_str} | Stock: {stock_text}"

    if p["notes"]:
        line += f" | Notes: {p['notes']}"
        for amt in extract_amounts(p["notes"]):
            known_amounts.add(amt)

    if p["description"]:
        for amt in extract_amounts(p["description"]):
            known_amounts.add(amt)

    return line


def build_context(
    conn: sqlite3.Connection,
    seller_id: int,
    message: str | None = None,
    *,
    max_products: int = 250,
    fts_threshold: int = 15,
    top_k: int = 6,
    prior_queries: list[str] | None = None,
) -> Context:
    """Build the context package for a given seller to feed the prompt.

    For small catalogues (<= fts_threshold products), includes the whole catalogue
    for 100% recall. For large catalogues (> fts_threshold products), uses SQLite FTS5
    and local embeddings fused via Reciprocal Rank Fusion (RRF) to retrieve top_k items.
    Collects all known prices and currency amounts from products and policies.
    """
    cur = conn.cursor()

    # Determine effective search query for multi-turn conversations
    search_message = message or ""
    if message and prior_queries:
        cleaned_words = re.findall(r"\b\w+\b", message.lower())
        is_short = len(cleaned_words) < 8
        has_pronoun = bool(set(cleaned_words) & PRONOUN_OR_SHORT_TOKENS)
        if (is_short or has_pronoun) and prior_queries:
            prior_text = prior_queries[-1].strip()
            search_message = f"{prior_text} {message}".strip()

    # 1. Shop details
    cur.execute(
        "SELECT id, slug, shop_name, description, tone, default_language "
        "FROM sellers WHERE id = ?;",
        (seller_id,),
    )
    seller_row = cur.fetchone()
    if not seller_row:
        raise ValueError(f"Seller with id {seller_id} not found.")

    cur.execute(
        "SELECT language FROM seller_languages WHERE seller_id = ? ORDER BY language ASC;",
        (seller_id,),
    )
    languages = [r["language"] for r in cur.fetchall()]

    shop = {
        "slug": seller_row["slug"],
        "name": seller_row["shop_name"],
        "description": seller_row["description"] or "",
        "tone": seller_row["tone"],
        "default_language": seller_row["default_language"],
        "languages": languages,
    }

    # 2. Products and variants
    known_amounts: set[int] = set()

    # Preload all known variant prices across the entire catalogue so guardrails remain 100% accurate
    cur.execute(
        """
        SELECT DISTINCT v.price_inr
        FROM product_variants v
        JOIN products p ON p.id = v.product_id
        WHERE p.seller_id = ?;
        """,
        (seller_id,),
    )
    for v_row in cur.fetchall():
        known_amounts.add(int(v_row["price_inr"]))

    # Check catalogue size
    cur.execute("SELECT COUNT(*) FROM products WHERE seller_id = ?;", (seller_id,))
    total_products = cur.fetchone()[0]

    product_rows: list[sqlite3.Row] = []
    retrieval_mode = "fts5_bm25"

    if total_products <= fts_threshold:
        # Small catalogue: inject complete catalogue for 100% recall
        cur.execute(
            """
            SELECT id, sku, name, category, description, attributes, stock_status, notes
            FROM products WHERE seller_id = ?
            ORDER BY id ASC
            LIMIT ?;
            """,
            (seller_id, max_products),
        )
        product_rows = cur.fetchall()
    else:
        # Large catalogue: hybrid retrieval using FTS5 and local embeddings via RRF
        fts_ids: list[int] = []
        if search_message:
            fts_rows = search_products_fts(conn, seller_id, search_message, limit=top_k * 2)
            fts_ids = [r["id"] for r in fts_rows]

        matched_ids: list[int] = fts_ids

        # Attempt semantic embedding ranking if search_message provided
        if search_message:
            query_emb = get_local_embedding(search_message)
            if query_emb:
                cur.execute(
                    "SELECT id, name, category, description FROM products WHERE seller_id = ?;",
                    (seller_id,),
                )
                prod_candidates = cur.fetchall()
                sim_scores = []
                for cand in prod_candidates:
                    cid = cand["id"]
                    text_repr = f"{cand['name']} {cand['category'] or ''} {cand['description'] or ''}".strip()
                    t_hash = hashlib.md5(text_repr.encode("utf-8")).hexdigest()
                    cache_key = (seller_id, cid, t_hash)
                    cand_emb = _EMBEDDING_CACHE.get(cache_key)
                    if cand_emb is None:
                        cand_emb = get_cached_embedding(conn, seller_id, str(cid), t_hash)
                        if cand_emb is not None:
                            _EMBEDDING_CACHE[cache_key] = cand_emb
                        else:
                            cand_emb = get_local_embedding(text_repr)
                            if cand_emb:
                                _EMBEDDING_CACHE[cache_key] = cand_emb
                                save_cached_embedding(conn, seller_id, str(cid), t_hash, cand_emb)
                    if cand_emb:
                        sim = cosine_similarity(query_emb, cand_emb)
                        sim_scores.append((cid, sim))

                if sim_scores:
                    sim_scores.sort(key=lambda x: x[1], reverse=True)
                    vector_ids = [cid for cid, _ in sim_scores]
                    matched_ids = reciprocal_rank_fusion(fts_ids, vector_ids, k=60)
                    retrieval_mode = "hybrid_rrf"

        selected_ids = matched_ids[:top_k]
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            cur.execute(
                f"""
                SELECT id, sku, name, category, description, attributes, stock_status, notes
                FROM products
                WHERE seller_id = ? AND id IN ({placeholders});
                """,
                (seller_id,) + tuple(selected_ids),
            )
            rows_by_id = {r["id"]: r for r in cur.fetchall()}
            product_rows = [rows_by_id[pid] for pid in selected_ids if pid in rows_by_id]

        # Backfill with remaining in-stock products if under top_k
        if len(product_rows) < top_k:
            remaining = top_k - len(product_rows)
            current_ids = [r["id"] for r in product_rows]
            if current_ids:
                placeholders = ",".join("?" for _ in current_ids)
                query = f"""
                    SELECT id, sku, name, category, description, attributes, stock_status, notes
                    FROM products
                    WHERE seller_id = ? AND id NOT IN ({placeholders})
                    ORDER BY CASE stock_status WHEN 'in_stock' THEN 1 WHEN 'low_stock' THEN 2 ELSE 3 END, id ASC
                    LIMIT ?;
                """
                params = (seller_id,) + tuple(current_ids) + (remaining,)
            else:
                query = """
                    SELECT id, sku, name, category, description, attributes, stock_status, notes
                    FROM products
                    WHERE seller_id = ?
                    ORDER BY CASE stock_status WHEN 'in_stock' THEN 1 WHEN 'low_stock' THEN 2 ELSE 3 END, id ASC
                    LIMIT ?;
                """
                params = (seller_id, remaining)

            cur.execute(query, params)
            product_rows.extend(cur.fetchall())

    catalogue_lines: list[str] = []
    for p in product_rows:
        pid = p["id"]
        cur.execute(
            "SELECT label, price_inr FROM product_variants WHERE product_id = ? ORDER BY price_inr ASC;",
            (pid,),
        )
        variant_rows = cur.fetchall()
        line = _format_product_line(p, variant_rows, known_amounts)
        catalogue_lines.append(line)

    catalogue_block = "\n".join(catalogue_lines)

    # 3. Policies
    cur.execute(
        "SELECT topic, title, body FROM policies WHERE seller_id = ? ORDER BY id ASC;",
        (seller_id,),
    )
    policy_rows = cur.fetchall()
    policy_lines: list[str] = []

    for pol in policy_rows:
        topic_upper = pol["topic"].upper()
        policy_lines.append(f"- {topic_upper} - {pol['title']}: {pol['body']}")
        for amt in extract_amounts(pol["body"]):
            known_amounts.add(amt)

    policies_block = "\n".join(policy_lines)

    # 4. Sample replies (few-shot)
    cur.execute(
        "SELECT language, customer_message, reply FROM sample_replies WHERE seller_id = ? ORDER BY id ASC;",
        (seller_id,),
    )
    all_samples = [
        {
            "language": r["language"],
            "customer_message": r["customer_message"],
            "reply": r["reply"],
        }
        for r in cur.fetchall()
    ]

    selected_samples: list[dict[str, str]] = []
    if message:
        msg_script = script_of(message)
        # Prioritize matching script
        matching = []
        others = []
        for s in all_samples:
            s_script = script_of(s["customer_message"])
            if s_script == msg_script:
                matching.append(s)
            else:
                others.append(s)
        selected_samples = (matching + others)[:3]
    else:
        selected_samples = all_samples[:3]

    return Context(
        shop=shop,
        catalogue_block=catalogue_block,
        policies_block=policies_block,
        examples=selected_samples,
        known_amounts=known_amounts,
        retrieval_mode=retrieval_mode,
        retrieved_products=product_rows,
    )
