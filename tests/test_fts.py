"""Dedicated unit tests for SQLite FTS5 catalogue search and real-time triggers."""

import sqlite3
import pytest
from engine.db import (
    connect,
    init_db,
    is_fts5_available,
    search_products_fts,
    search_products_full,
    sanitize_fts_query,
)


@pytest.fixture
def fts_db(tmp_path):
    """Create a temporary database with schema and FTS5 initialized."""
    db_file = tmp_path / "test_fts.db"
    init_db(str(db_file))
    conn = connect(str(db_file))

    # Create test seller
    conn.execute(
        """
        INSERT INTO sellers (slug, shop_name, tone, default_language)
        VALUES ('test_shop', 'Test Shop', 'friendly', 'en');
        """
    )
    seller_id = 1

    # Insert products with variants
    conn.execute(
        """
        INSERT INTO products (seller_id, sku, name, category, description, notes)
        VALUES (1, 'SKU-01', 'Pure Cotton Kurti', 'Apparel', 'Comfortable blue daily wear cotton kurti', 'Wash cold');
        """
    )
    conn.execute(
        """
        INSERT INTO product_variants (product_id, label, price_inr)
        VALUES (1, 'M', 899), (1, 'L', 899);
        """
    )

    conn.execute(
        """
        INSERT INTO products (seller_id, sku, name, category, description, notes)
        VALUES (1, 'SKU-02', 'Silk Anarkali Kurti', 'Apparel', 'Festive red embroidery anarkali suit', 'Dry clean only');
        """
    )
    conn.execute(
        """
        INSERT INTO product_variants (product_id, label, price_inr)
        VALUES (2, 'Free Size', 1499);
        """
    )

    conn.execute(
        """
        INSERT INTO products (seller_id, sku, name, category, description, notes)
        VALUES (1, 'SKU-03', 'चॉकलेट केक', 'बेकरी', 'ताजा बेक केलेला डार्क चॉकलेट ट्रफल केक', 'अंडारहित');
        """
    )
    conn.execute(
        """
        INSERT INTO product_variants (product_id, label, price_inr)
        VALUES (3, '500g', 650);
        """
    )

    conn.commit()
    conn.close()
    return str(db_file)


def test_fts5_is_available(fts_db):
    conn = connect(fts_db)
    assert is_fts5_available(conn) is True
    conn.close()


def test_fts_table_and_triggers_exist(fts_db):
    conn = connect(fts_db)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products_fts';")
    assert cur.fetchone() is not None

    cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_products_fts_%';")
    triggers = {r["name"] for r in cur.fetchall()}
    assert {"trg_products_fts_ai", "trg_products_fts_ad", "trg_products_fts_au"}.issubset(triggers)
    conn.close()


def test_fts_search_ranking(fts_db):
    conn = connect(fts_db)
    # Searching for "pure cotton" should rank SKU-01 top
    res = search_products_fts(conn, 1, "pure cotton kurti")
    assert len(res) >= 1
    assert res[0]["sku"] == "SKU-01"

    # Searching for "festive anarkali" should rank SKU-02 top
    res_festive = search_products_fts(conn, 1, "festive anarkali")
    assert len(res_festive) >= 1
    assert res_festive[0]["sku"] == "SKU-02"
    conn.close()


def test_fts_devanagari_search(fts_db):
    conn = connect(fts_db)
    # Search with Marathi / Hindi Devanagari keywords
    res = search_products_fts(conn, 1, "मला डार्क चॉकलेट केक हवा आहे")
    assert len(res) >= 1
    assert res[0]["sku"] == "SKU-03"
    assert "चॉकलेट" in res[0]["name"]
    conn.close()


def test_fts_insert_trigger(fts_db):
    conn = connect(fts_db)
    conn.execute(
        """
        INSERT INTO products (seller_id, sku, name, category, description, notes)
        VALUES (1, 'SKU-04', 'Oxidised Silver Jhumka', 'Jewellery', 'Traditional handcrafted earrings', 'Lead free');
        """
    )
    conn.commit()

    # Verify immediately searchable via FTS5
    res = search_products_fts(conn, 1, "silver jhumka earrings")
    assert len(res) == 1
    assert res[0]["sku"] == "SKU-04"
    conn.close()


def test_fts_update_trigger(fts_db):
    conn = connect(fts_db)
    # Update SKU-01 to linen fabric
    conn.execute(
        """
        UPDATE products
        SET name = 'Linen Summer Shirt', description = 'Breathable white linen casual shirt'
        WHERE sku = 'SKU-01';
        """
    )
    conn.commit()

    # Search for new keyword 'linen'
    res_new = search_products_fts(conn, 1, "linen shirt")
    assert len(res_new) == 1
    assert res_new[0]["sku"] == "SKU-01"

    # Old keyword 'cotton' should no longer match SKU-01
    res_old = search_products_fts(conn, 1, "pure cotton")
    skus = [r["sku"] for r in res_old]
    assert "SKU-01" not in skus
    conn.close()


def test_fts_delete_trigger(fts_db):
    conn = connect(fts_db)
    # Delete SKU-02
    conn.execute("DELETE FROM products WHERE sku = 'SKU-02';")
    conn.commit()

    # Search for 'anarkali' should be empty
    res = search_products_fts(conn, 1, "anarkali")
    assert len(res) == 0
    conn.close()


def test_fts_query_sanitizer_resilience():
    # Test that complex punctuation and operators do not raise syntax errors
    dirty_inputs = [
        "What is the price of (kurti) * 50% off???",
        "Hello 'world' \"quote\" NOT AND OR: test!",
        "??? !!! @@@ ### $$$ %%% ^^^ &&&",
        "पुणे में डिलीवरी! (1-2 days?)",
        "",
        "   ",
    ]
    for inp in dirty_inputs:
        sanitized = sanitize_fts_query(inp)
        assert isinstance(sanitized, str)


def test_search_products_full(fts_db):
    conn = connect(fts_db)
    # Search for kurti
    prods = search_products_full(conn, 1, "cotton kurti")
    assert len(prods) >= 1
    p = prods[0]
    assert p["sku"] == "SKU-01"
    assert len(p["variants"]) == 2
    assert p["variants"][0]["price_inr"] == 899

    # Empty search query returns all products for the seller
    all_prods = search_products_full(conn, 1, "")
    assert len(all_prods) == 3
    conn.close()
