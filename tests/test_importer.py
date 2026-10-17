"""Tests for config validation, JSON import/export round-trip, and CSV import."""

import json
from pathlib import Path
import pytest
from engine.db import connect, init_db
from engine.importer import (
    ConfigError,
    export_config,
    import_config,
    import_products_csv,
    validate_config,
)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_importer.db"
    init_db(str(db_file))
    return str(db_file)


def test_validate_all_sample_shops():
    sample_files = ["urban_thread.json", "sweet_crumbs.json", "kalakruti_jewels.json"]
    for fname in sample_files:
        fpath = CONFIG_DIR / fname
        data = json.loads(fpath.read_text(encoding="utf-8"))
        # Should validate without error
        validate_config(data)


def test_validate_config_rejects_missing_default_language():
    fpath = CONFIG_DIR / "urban_thread.json"
    data = json.loads(fpath.read_text(encoding="utf-8"))
    data["shop"]["default_language"] = "fr"  # not in enum and not in languages
    with pytest.raises(ConfigError):
        validate_config(data)


def test_import_and_export_roundtrip(temp_db):
    conn = connect(temp_db)
    sample_files = ["urban_thread.json", "sweet_crumbs.json", "kalakruti_jewels.json"]

    for fname in sample_files:
        fpath = CONFIG_DIR / fname
        original_data = json.loads(fpath.read_text(encoding="utf-8"))

        seller_id = import_config(conn, original_data, replace=True)
        assert seller_id > 0

        # Export and verify
        exported = export_config(conn, original_data["shop"]["slug"])
        assert exported["shop"]["name"] == original_data["shop"]["name"]
        assert len(exported["products"]) == len(original_data["products"])
        assert len(exported["policies"]) == len(original_data["policies"])
        assert len(exported["sample_replies"]) == len(original_data["sample_replies"])

        # Re-import exported data to verify losslessness
        reimported_id = import_config(conn, exported, replace=True)
        assert reimported_id > 0

    conn.close()


def test_import_products_csv(temp_db, tmp_path):
    conn = connect(temp_db)
    # First import urban_thread
    fpath = CONFIG_DIR / "urban_thread.json"
    data = json.loads(fpath.read_text(encoding="utf-8"))
    import_config(conn, data)

    # Create test CSV with formatted currency and empty variant_label
    csv_file = tmp_path / "products.csv"
    csv_file.write_text(
        "sku,name,category,description,variant_label,price_inr,stock_status,sizes,colors,notes\n"
        "CSV-01,Summer Top,Tops,Light cotton top,Small,₹ 499,in_stock,S;M;L,Yellow;Pink,Wash cold\n"
        "CSV-01,Summer Top,Tops,Light cotton top,Large,549.00,in_stock,S;M;L,Yellow;Pink,Wash cold\n"
        'CSV-02,Linen Scarf,Accessories,Handloom scarf,,"Rs. 1,299/-",in_stock,,Blue,\n',
        encoding="utf-8",
    )

    imported_count = import_products_csv(conn, "urban_thread", str(csv_file))
    assert imported_count == 2

    # Check database
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM products WHERE sku = 'CSV-01';")
    p = cur.fetchone()
    assert p is not None
    assert p["name"] == "Summer Top"

    cur.execute("SELECT price_inr FROM product_variants WHERE product_id = ? ORDER BY price_inr ASC;", (p["id"],))
    prices = [r["price_inr"] for r in cur.fetchall()]
    assert prices == [499, 549]

    # Check CSV-02 parsed blank label as 'Standard' and price as 1299
    cur.execute("SELECT id FROM products WHERE sku = 'CSV-02';")
    p2 = cur.fetchone()
    cur.execute("SELECT label, price_inr FROM product_variants WHERE product_id = ?;", (p2["id"],))
    v2 = cur.fetchone()
    assert v2["label"] == "Standard"
    assert v2["price_inr"] == 1299
    conn.close()


def test_seller_faq_survives_reimport(temp_db):
    from engine.db import save_faq_pair, search_products_fts

    conn = connect(temp_db)
    fpath = CONFIG_DIR / "urban_thread.json"
    data = json.loads(fpath.read_text(encoding="utf-8"))

    # Initial import
    seller_id = import_config(conn, data, replace=True)

    # Save custom seller FAQ pair
    faq_id = save_faq_pair(
        conn,
        seller_id=seller_id,
        question="Can I get premium gift packaging?",
        reply="Yes, premium gift packaging is available for ₹75 extra.",
        topic="ordering",
    )
    assert faq_id > 0

    # Verify products are searchable via FTS5
    initial_matches = search_products_fts(conn, seller_id, "cotton kurti")
    assert len(initial_matches) > 0

    # Re-import shop with replace=True (simulates re-running import_config or verify_shops)
    reimported_id = import_config(conn, data, replace=True)
    assert reimported_id == seller_id

    # Verify seller FAQ survived in policies
    cur = conn.cursor()
    cur.execute("SELECT id, topic, title, body, source_type FROM policies WHERE id = ?;", (faq_id,))
    preserved_policy = cur.fetchone()
    assert preserved_policy is not None
    assert preserved_policy["source_type"] == "seller_faq"
    assert "₹75" in preserved_policy["body"]

    # Verify seller FAQ survived in sample_replies
    cur.execute("SELECT id, customer_message, reply, source_type FROM sample_replies WHERE seller_id = ? AND source_type = 'seller_faq';", (seller_id,))
    preserved_sample = cur.fetchone()
    assert preserved_sample is not None
    assert "premium gift packaging" in preserved_sample["customer_message"]

    # Verify products remain searchable in FTS5 after re-import FTS rebuild
    rebuilt_matches = search_products_fts(conn, seller_id, "cotton kurti")
    assert len(rebuilt_matches) > 0
    assert any("Kurti" in m["name"] for m in rebuilt_matches)

    conn.close()
