"""Database operations, connection management, and queries for ReplyDesk."""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from engine.config import load_settings

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
FTS_FILE = Path(__file__).resolve().parent.parent / "db" / "fts.sql"


def is_fts5_available(conn: sqlite3.Connection) -> bool:
    """Check if the SQLite build supports FTS5."""
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA compile_options;")
        options = {row[0] for row in cur.fetchall()}
        if "ENABLE_FTS5" in options:
            return True
        cur.execute("SELECT 1 FROM pragma_module_list WHERE name = 'fts5';")
        return cur.fetchone() is not None
    except Exception:
        return False


def init_fts(conn: sqlite3.Connection) -> bool:
    """Initialize FTS5 virtual table and synchronization triggers if supported."""
    if not is_fts5_available(conn):
        return False

    try:
        cur = conn.cursor()
        # Base products table must exist before setting up FTS5
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products';")
        if not cur.fetchone():
            return False

        # Check if FTS sync triggers are already installed
        cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='trg_products_fts_ai';")
        if not cur.fetchone():
            if not FTS_FILE.exists():
                return False
            fts_sql = FTS_FILE.read_text(encoding="utf-8")
            conn.executescript(fts_sql)
            conn.commit()
        return True
    except Exception:
        return False


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode, foreign keys enabled, and row_factory configured."""
    if db_path is None:
        try:
            settings = load_settings()
            db_path = settings.db_path
        except Exception:
            db_path = os.getenv("DB_PATH", "data/replydesk.db")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # WAL mode allows concurrent readers and writers across multi-window Streamlit sessions
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA cache_size = -64000;")
    init_fts(conn)
    return conn


def init_db(db_path: str | None = None) -> None:
    """Initialize database from db/schema.sql if user_version is 0."""
    conn = connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA user_version;")
        row = cur.fetchone()
        version = row[0] if row else 0

        if version == 0:
            if not SCHEMA_FILE.exists():
                raise FileNotFoundError(f"Schema file not found at {SCHEMA_FILE}")
            schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
            conn.executescript(schema_sql)
            conn.commit()

        init_fts(conn)
    finally:
        conn.close()


def get_seller_by_slug(conn: sqlite3.Connection, slug: str) -> sqlite3.Row | None:
    """Look up a seller by unique slug."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, slug, shop_name, description, tone, default_language, created_at, updated_at "
        "FROM sellers WHERE slug = ?;",
        (slug,),
    )
    return cur.fetchone()


def get_seller_by_id(conn: sqlite3.Connection, seller_id: int) -> sqlite3.Row | None:
    """Look up a seller by primary key."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, slug, shop_name, description, tone, default_language, created_at, updated_at "
        "FROM sellers WHERE id = ?;",
        (seller_id,),
    )
    return cur.fetchone()


def list_sellers(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all sellers ordered by shop name."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, slug, shop_name, description, tone, default_language, created_at, updated_at "
        "FROM sellers ORDER BY shop_name ASC;"
    )
    return cur.fetchall()


def log_reply(
    conn: sqlite3.Connection,
    seller_id: int,
    customer_message: str,
    drafted_reply: str,
    model: str,
    detected_language: str | None = None,
    needs_check: bool = False,
    check_reason: str | None = None,
    ungrounded_amounts: list[int] | None = None,
    risk_topics: list[str] | None = None,
    latency_ms: int | None = None,
    seller_action: str | None = None,
    final_reply: str | None = None,
) -> int:
    """Insert a draft into reply_log and return the generated row id."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reply_log (
                seller_id, customer_message, detected_language, drafted_reply,
                needs_check, check_reason, ungrounded_amounts, risk_topics,
                model, latency_ms, seller_action, final_reply
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                seller_id,
                customer_message,
                detected_language,
                drafted_reply,
                1 if needs_check else 0,
                check_reason or "",
                json.dumps(ungrounded_amounts or []),
                json.dumps(risk_topics or []),
                model,
                latency_ms,
                seller_action,
                final_reply,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def set_reply_action(
    conn: sqlite3.Connection,
    reply_id: int,
    action: str,
    final_reply: str | None = None,
) -> None:
    """Update seller action ('sent_as_is', 'edited', 'discarded') and optional final reply."""
    if action not in ("sent_as_is", "edited", "discarded"):
        raise ValueError(f"Invalid seller action: {action}")
    with conn:
        conn.execute(
            "UPDATE reply_log SET seller_action = ?, final_reply = ? WHERE id = ?;",
            (action, final_reply, reply_id),
        )


def clear_history(conn: sqlite3.Connection, seller_id: int) -> int:
    """Delete all reply_log rows for a seller."""
    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM reply_log WHERE seller_id = ?;", (seller_id,))
        return cur.rowcount


def list_pending_replies(conn: sqlite3.Connection, seller_id: int) -> list[sqlite3.Row]:
    """List pending drafts (seller_action IS NULL) for a seller, newest first."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, customer_message, detected_language, drafted_reply,
               needs_check, check_reason, ungrounded_amounts, risk_topics,
               model, latency_ms, created_at
        FROM reply_log
        WHERE seller_id = ? AND seller_action IS NULL
        ORDER BY created_at DESC, id DESC;
        """,
        (seller_id,),
    )
    return cur.fetchall()


def get_reply_by_id(conn: sqlite3.Connection, reply_id: int) -> sqlite3.Row | None:
    """Fetch a single reply_log row by id."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, seller_id, customer_message, detected_language, drafted_reply,
               needs_check, check_reason, ungrounded_amounts, risk_topics,
               model, latency_ms, seller_action, final_reply, created_at
        FROM reply_log
        WHERE id = ?;
        """,
        (reply_id,),
    )
    return cur.fetchone()

def list_history(
    conn: sqlite3.Connection,
    seller_id: int,
    action_filter: str | None = None,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    """Fetch history rows for a seller, newest first, with optional action filter and limit."""
    cur = conn.cursor()
    query = """
        SELECT * FROM reply_log
        WHERE seller_id = ?
    """
    params: list[Any] = [seller_id]

    if action_filter and action_filter != "all":
        if action_filter == "pending":
            query += " AND seller_action IS NULL"
        else:
            query += " AND seller_action = ?"
            params.append(action_filter)

    query += " ORDER BY created_at DESC, id DESC"

    if limit is not None and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    cur.execute(query, tuple(params))
    return cur.fetchall()


def list_products_full(conn: sqlite3.Connection, seller_id: int) -> list[dict[str, Any]]:
    """Return all products with their variants for a seller."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, sku, name, category, description, attributes, stock_status, notes
        FROM products WHERE seller_id = ? ORDER BY id ASC;
        """,
        (seller_id,),
    )
    products = []
    for p in cur.fetchall():
        pid = p["id"]
        cur.execute(
            "SELECT id, label, price_inr FROM product_variants WHERE product_id = ? ORDER BY id ASC;",
            (pid,),
        )
        variants = [{"id": v["id"], "label": v["label"], "price_inr": v["price_inr"]} for v in cur.fetchall()]
        attrs = {}
        if p["attributes"]:
            try:
                attrs = json.loads(p["attributes"])
            except Exception:
                attrs = {}
        products.append({
            "id": p["id"],
            "sku": p["sku"],
            "name": p["name"],
            "category": p["category"] or "",
            "description": p["description"] or "",
            "attributes": attrs,
            "stock_status": p["stock_status"],
            "notes": p["notes"] or "",
            "variants": variants,
        })
    return products


def sanitize_fts_query(text: str) -> str:
    """Extract valid alphanumeric words across Latin, digits, and Devanagari scripts for FTS5."""
    tokens = re.findall(r"[a-zA-Z0-9_\u0900-\u097F]+", text)
    clean_tokens = [f'"{tok}"*' for tok in tokens if len(tok) >= 2]
    return " OR ".join(clean_tokens)


def search_products_fts(
    conn: sqlite3.Connection,
    seller_id: int,
    query_text: str,
    limit: int = 10,
) -> list[sqlite3.Row]:
    """Search products using SQLite FTS5 BM25 ranking for a seller."""
    if not is_fts5_available(conn):
        return []

    sanitized = sanitize_fts_query(query_text)
    if not sanitized:
        return []

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT p.id, p.sku, p.name, p.category, p.description, p.attributes, p.stock_status, p.notes,
                   f.rank AS fts_rank
            FROM products_fts f
            JOIN products p ON p.id = f.rowid
            WHERE products_fts MATCH ? AND p.seller_id = ?
            ORDER BY f.rank ASC
            LIMIT ?;
            """,
            (sanitized, seller_id, limit),
        )
        return cur.fetchall()
    except sqlite3.OperationalError:
        return []


def search_products_full(
    conn: sqlite3.Connection,
    seller_id: int,
    query_text: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search products with variants for a seller, with fallback to all products if query empty."""
    if not query_text.strip():
        return list_products_full(conn, seller_id)

    matching_rows = search_products_fts(conn, seller_id, query_text, limit=limit)
    if not matching_rows:
        return []

    cur = conn.cursor()
    products = []
    for p in matching_rows:
        pid = p["id"]
        cur.execute(
            "SELECT id, label, price_inr FROM product_variants WHERE product_id = ? ORDER BY id ASC;",
            (pid,),
        )
        variants = [{"id": v["id"], "label": v["label"], "price_inr": v["price_inr"]} for v in cur.fetchall()]
        attrs = {}
        if p["attributes"]:
            try:
                attrs = json.loads(p["attributes"])
            except Exception:
                attrs = {}
        products.append({
            "id": p["id"],
            "sku": p["sku"],
            "name": p["name"],
            "category": p["category"] or "",
            "description": p["description"] or "",
            "attributes": attrs,
            "stock_status": p["stock_status"],
            "notes": p["notes"] or "",
            "variants": variants,
        })
    return products


def list_policies(conn: sqlite3.Connection, seller_id: int) -> list[sqlite3.Row]:
    """Return policies for a seller."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, topic, title, body FROM policies WHERE seller_id = ? ORDER BY id ASC;",
        (seller_id,),
    )
    return cur.fetchall()


def list_sample_replies(conn: sqlite3.Connection, seller_id: int) -> list[sqlite3.Row]:
    """Return sample replies for a seller."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, language, customer_message, reply FROM sample_replies WHERE seller_id = ? ORDER BY id ASC;",
        (seller_id,),
    )
    return cur.fetchall()


def save_shop_details(
    conn: sqlite3.Connection,
    seller_id: int,
    name: str,
    description: str,
    tone: str,
    default_language: str,
    languages: list[str],
) -> None:
    """Update shop details and supported languages."""
    with conn:
        conn.execute(
            """
            UPDATE sellers
            SET shop_name = ?, description = ?, tone = ?, default_language = ?, updated_at = datetime('now')
            WHERE id = ?;
            """,
            (name, description, tone, default_language, seller_id),
        )
        conn.execute("DELETE FROM seller_languages WHERE seller_id = ?;", (seller_id,))
        for lang in languages:
            conn.execute(
                "INSERT INTO seller_languages (seller_id, language) VALUES (?, ?);",
                (seller_id, lang),
            )


def add_or_update_product(
    conn: sqlite3.Connection,
    seller_id: int,
    sku: str,
    name: str,
    category: str,
    description: str,
    attributes: dict,
    stock_status: str,
    notes: str,
    variants: list[dict],
) -> int:
    """Insert or update a product and its variants."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO products (
                seller_id, sku, name, category, description, attributes, stock_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(seller_id, sku) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                description = excluded.description,
                attributes = excluded.attributes,
                stock_status = excluded.stock_status,
                notes = excluded.notes;
            """,
            (
                seller_id,
                sku,
                name,
                category or None,
                description or None,
                json.dumps(attributes),
                stock_status,
                notes or None,
            ),
        )
        cur.execute("SELECT id FROM products WHERE seller_id = ? AND sku = ?;", (seller_id, sku))
        product_id = cur.fetchone()["id"]

        # Upsert variants preserving existing variants for multi-variant products
        for v in variants:
            conn.execute(
                """
                INSERT INTO product_variants (product_id, label, price_inr)
                VALUES (?, ?, ?)
                ON CONFLICT(product_id, label) DO UPDATE SET
                    price_inr = excluded.price_inr;
                """,
                (product_id, v["label"], int(v["price_inr"])),
            )
        return product_id


def delete_product(conn: sqlite3.Connection, product_id: int) -> None:
    """Delete a product by id (cascades delete variants)."""
    with conn:
        conn.execute("DELETE FROM products WHERE id = ?;", (product_id,))


def add_policy(conn: sqlite3.Connection, seller_id: int, topic: str, title: str, body: str) -> int:
    """Insert or update a policy."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO policies (seller_id, topic, title, body)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(seller_id, topic, title) DO UPDATE SET
                body = excluded.body;
            """,
            (seller_id, topic, title, body),
        )
        return cur.lastrowid  # type: ignore[return-value]


def delete_policy(conn: sqlite3.Connection, policy_id: int) -> None:
    """Delete a policy by id."""
    with conn:
        conn.execute("DELETE FROM policies WHERE id = ?;", (policy_id,))


def add_sample_reply(
    conn: sqlite3.Connection,
    seller_id: int,
    language: str,
    customer_message: str,
    reply: str,
) -> int:
    """Insert a sample reply."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sample_replies (seller_id, language, customer_message, reply)
            VALUES (?, ?, ?, ?);
            """,
            (seller_id, language, customer_message, reply),
        )
        return cur.lastrowid  # type: ignore[return-value]


def delete_sample_reply(conn: sqlite3.Connection, sample_id: int) -> None:
    """Delete a sample reply by id."""
    with conn:
        conn.execute("DELETE FROM sample_replies WHERE id = ?;", (sample_id,))


def create_eval_run(
    conn: sqlite3.Connection,
    model: str,
    notes: str | None = None,
) -> int:
    """Create a new evaluation run record and return run_id."""
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO eval_runs (model, notes, started_at)
            VALUES (?, ?, datetime('now'));
            """,
            (model, notes),
        )
        assert cur.lastrowid is not None
        return cur.lastrowid


def record_eval_result(
    conn: sqlite3.Connection,
    run_id: int,
    case_id: str,
    shop_slug: str,
    language: str,
    category: str,
    split: str | None,
    reply: str,
    needs_check: bool,
    facts_ok: bool,
    needs_check_ok: bool,
    language_ok: bool,
    language_label_ok: bool | None,
    latency_ms: int,
    prompt_tokens: int | None = None,
    output_tokens: int | None = None,
    tone_score: int | None = None,
) -> None:
    """Record a single evaluation test case result."""
    with conn:
        conn.execute(
            """
            INSERT INTO eval_results (
                run_id, case_id, shop_slug, language, category, split,
                reply, needs_check, facts_ok, needs_check_ok, language_ok,
                language_label_ok, latency_ms, prompt_tokens, output_tokens, tone_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, case_id) DO UPDATE SET
                reply = excluded.reply,
                needs_check = excluded.needs_check,
                facts_ok = excluded.facts_ok,
                needs_check_ok = excluded.needs_check_ok,
                language_ok = excluded.language_ok,
                language_label_ok = excluded.language_label_ok,
                latency_ms = excluded.latency_ms,
                prompt_tokens = excluded.prompt_tokens,
                output_tokens = excluded.output_tokens,
                tone_score = excluded.tone_score;
            """,
            (
                run_id,
                case_id,
                shop_slug,
                language,
                category,
                split,
                reply,
                1 if needs_check else 0,
                1 if facts_ok else 0,
                1 if needs_check_ok else 0,
                1 if language_ok else 0,
                None if language_label_ok is None else (1 if language_label_ok else 0),
                latency_ms,
                prompt_tokens,
                output_tokens,
                tone_score,
            ),
        )


def finish_eval_run(conn: sqlite3.Connection, run_id: int) -> None:
    """Mark an evaluation run as completed with timestamp."""
    with conn:
        conn.execute(
            "UPDATE eval_runs SET finished_at = datetime('now') WHERE id = ?;",
            (run_id,),
        )


def list_eval_runs(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    """List past evaluation runs, newest first."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.id, r.model, r.notes, r.started_at, r.finished_at,
               COUNT(res.id) AS total_cases,
               SUM(res.facts_ok) AS passed_facts,
               SUM(res.needs_check_ok) AS passed_needs_check,
               SUM(res.language_ok) AS passed_language,
               SUM(CASE WHEN res.facts_ok = 1 AND res.needs_check_ok = 1 AND res.language_ok = 1 THEN 1 ELSE 0 END) AS passed_total,
               AVG(res.latency_ms) AS avg_latency_ms
        FROM eval_runs r
        LEFT JOIN eval_results res ON res.run_id = r.id
        GROUP BY r.id
        ORDER BY r.id DESC
        LIMIT ?;
        """,
        (limit,),
    )
    return cur.fetchall()


def get_eval_run(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row | None:
    """Fetch single evaluation run by id."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM eval_runs WHERE id = ?;", (run_id,))
    return cur.fetchone()


def get_eval_results(conn: sqlite3.Connection, run_id: int) -> list[sqlite3.Row]:
    """Fetch all test case results for an evaluation run."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM eval_results
        WHERE run_id = ?
        ORDER BY id ASC;
        """,
        (run_id,),
    )
    return cur.fetchall()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
        print("Database initialized successfully.")
    else:
        print("Usage: python -m engine.db init")
