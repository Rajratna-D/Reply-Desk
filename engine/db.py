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
    """Open a SQLite connection with foreign keys enabled and row_factory configured."""
    if db_path is None:
        try:
            settings = load_settings()
            db_path = settings.db_path
        except Exception:
            db_path = os.getenv("DB_PATH", "data/replydesk.db")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
        print("Database initialized successfully.")
    else:
        print("Usage: python -m engine.db init")
