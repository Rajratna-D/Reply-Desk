"""Tests for database initialization, constraints, and foreign keys."""

import sqlite3
import pytest
from engine.db import connect, init_db, get_seller_by_slug


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database with schema initialized."""
    db_file = tmp_path / "test.db"
    init_db(str(db_file))
    return str(db_file)


def test_init_db_creates_tables(temp_db):
    conn = connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row["name"] for row in cur.fetchall()}
    conn.close()

    expected = {
        "sellers",
        "seller_languages",
        "products",
        "product_variants",
        "policies",
        "sample_replies",
        "reply_log",
        "eval_runs",
        "eval_results",
    }
    assert expected.issubset(tables)


def test_foreign_keys_enforced(temp_db):
    conn = connect(temp_db)
    with pytest.raises(sqlite3.IntegrityError):
        # Insert product with non-existent seller_id 999
        conn.execute(
            """
            INSERT INTO products (seller_id, sku, name)
            VALUES (999, 'SKU-01', 'Test Product');
            """
        )
    conn.close()


def test_slug_constraints(temp_db):
    conn = connect(temp_db)
    # Invalid slug with uppercase letters
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO sellers (slug, shop_name, tone, default_language)
            VALUES ('InvalidSlug', 'Shop', 'friendly', 'en');
            """
        )

    # Valid slug
    conn.execute(
        """
        INSERT INTO sellers (slug, shop_name, tone, default_language)
        VALUES ('valid_slug_123', 'Shop', 'friendly', 'en');
        """
    )
    conn.commit()
    conn.close()


def test_negative_price_rejected(temp_db):
    conn = connect(temp_db)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sellers (slug, shop_name, tone, default_language)
        VALUES ('test_shop', 'Shop', 'friendly', 'en');
        """
    )
    seller_id = cur.lastrowid
    cur.execute(
        """
        INSERT INTO products (seller_id, sku, name)
        VALUES (?, 'SKU-1', 'Product 1');
        """,
        (seller_id,),
    )
    product_id = cur.lastrowid

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO product_variants (product_id, label, price_inr)
            VALUES (?, 'Regular', -100);
            """,
            (product_id,),
        )
    conn.close()


def test_cascade_delete(temp_db):
    conn = connect(temp_db)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sellers (slug, shop_name, tone, default_language)
        VALUES ('delete_shop', 'Shop', 'friendly', 'en');
        """
    )
    seller_id = cur.lastrowid
    cur.execute(
        "INSERT INTO products (seller_id, sku, name) VALUES (?, 'P1', 'Name');",
        (seller_id,),
    )
    pid = cur.lastrowid
    cur.execute(
        "INSERT INTO product_variants (product_id, label, price_inr) VALUES (?, 'Std', 100);",
        (pid,),
    )
    conn.commit()

    # Delete seller
    conn.execute("DELETE FROM sellers WHERE id = ?;", (seller_id,))
    conn.commit()

    # Check products and variants are gone
    cur.execute("SELECT COUNT(*) FROM products WHERE seller_id = ?;", (seller_id,))
    assert cur.fetchone()[0] == 0

    cur.execute("SELECT COUNT(*) FROM product_variants WHERE product_id = ?;", (pid,))
    assert cur.fetchone()[0] == 0
    conn.close()
