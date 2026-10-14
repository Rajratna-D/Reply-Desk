"""Context retrieval and prompt block formatting for ReplyDesk."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from engine.db import search_products_fts
from engine.guardrails import extract_amounts, script_of


@dataclass
class Context:
    shop: dict[str, Any]
    catalogue_block: str
    policies_block: str
    examples: list[dict[str, str]]
    known_amounts: set[int]


STOCK_STATUS_MAP = {
    "in_stock": "in stock",
    "low_stock": "low stock (limited)",
    "out_of_stock": "out of stock",
    "made_to_order": "made to order",
}


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
) -> Context:
    """Build the context package for a given seller to feed the prompt.

    For small catalogues (<= fts_threshold products), includes the whole catalogue
    for 100% recall. For large catalogues (> fts_threshold products), uses SQLite FTS5
    to retrieve the top_k most relevant products for the customer message.
    Collects all known prices and currency amounts from products and policies.
    """
    cur = conn.cursor()

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
        # Large catalogue: use FTS5 smart retrieval based on customer query
        matched_ids: list[int] = []
        if message:
            fts_rows = search_products_fts(conn, seller_id, message, limit=top_k)
            for r in fts_rows:
                product_rows.append(r)
                matched_ids.append(r["id"])

        # Backfill with remaining in-stock products if under top_k
        if len(product_rows) < top_k:
            remaining = top_k - len(product_rows)
            if matched_ids:
                placeholders = ",".join("?" for _ in matched_ids)
                query = f"""
                    SELECT id, sku, name, category, description, attributes, stock_status, notes
                    FROM products
                    WHERE seller_id = ? AND id NOT IN ({placeholders})
                    ORDER BY CASE stock_status WHEN 'in_stock' THEN 1 WHEN 'low_stock' THEN 2 ELSE 3 END, id ASC
                    LIMIT ?;
                """
                params = (seller_id,) + tuple(matched_ids) + (remaining,)
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
    )
