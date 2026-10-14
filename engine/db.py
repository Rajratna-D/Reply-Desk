"""Database operations, connection management, and queries for ReplyDesk."""

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from engine.config import load_settings

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


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


def delete_seller(conn: sqlite3.Connection, seller_id: int) -> None:
    """Delete a seller and all children."""
    with conn:
        conn.execute("DELETE FROM sellers WHERE id = ?;", (seller_id,))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
        print("Database initialized successfully.")
    else:
        print("Usage: python -m engine.db init")
