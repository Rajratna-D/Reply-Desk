"""Tests for retrieval context generation and prompt block construction."""

import json
from pathlib import Path
import pytest
from engine.db import connect, init_db
from engine.importer import import_config
from engine.retrieval import build_context

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture
def populated_db(tmp_path):
    db_file = tmp_path / "test_retrieval.db"
    init_db(str(db_file))
    conn = connect(str(db_file))

    for fname in ["urban_thread.json", "sweet_crumbs.json"]:
        fpath = CONFIG_DIR / fname
        data = json.loads(fpath.read_text(encoding="utf-8"))
        import_config(conn, data)

    conn.close()
    return str(db_file)


def test_build_context_catalogue_and_policies(populated_db):
    conn = connect(populated_db)
    # Check urban thread (seller_id 1)
    ctx = build_context(conn, 1)

    assert ctx.shop["name"] == "Urban Thread"
    assert "Cotton Kurti" in ctx.catalogue_block
    assert "₹899" in ctx.catalogue_block
    assert "DELIVERY" in ctx.policies_block
    assert "RETURNS" in ctx.policies_block

    # Known amounts should include variant prices (899, 1499, 599, 349) and policy numbers (60, 1000)
    assert {899, 1499, 599, 349, 60, 1000}.issubset(ctx.known_amounts)
    conn.close()


def test_build_context_script_preference(populated_db):
    conn = connect(populated_db)
    # Devanagari query
    ctx_hi = build_context(conn, 1, message="कुर्ती की कीमत क्या है?")
    # First example should be in Devanagari
    first_ex = ctx_hi.examples[0]
    assert first_ex["language"] in ("hi", "mr")

    # Latin query
    ctx_en = build_context(conn, 1, message="How much is the kurti?")
    first_ex_en = ctx_en.examples[0]
    assert first_ex_en["language"] in ("en", "hinglish")

    conn.close()
