"""Smoke test calling Ollama, automatically skipped if Ollama is not running."""

import json
import os
from pathlib import Path
import pytest
from engine.config import load_settings
from engine.db import connect, init_db
from engine.importer import import_config
from engine.llm import ollama_status
from engine.service import draft_reply

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture
def smoke_db(tmp_path):
    db_file = tmp_path / "smoke.db"
    init_db(str(db_file))
    conn = connect(str(db_file))
    fpath = CONFIG_DIR / "urban_thread.json"
    data = json.loads(fpath.read_text(encoding="utf-8"))
    import_config(conn, data)
    conn.close()
    return str(db_file)


def test_model_smoke(smoke_db):
    try:
        settings = load_settings(db_path=smoke_db)
    except Exception as e:
        pytest.skip(f"Settings error: {e}")

    status = ollama_status(settings.ollama_host)
    if not status["reachable"]:
        pytest.skip(f"Ollama server not reachable at {settings.ollama_host}")

    if settings.model_name not in status["models"]:
        pytest.skip(f"Model '{settings.model_name}' not pulled in Ollama")

    draft = draft_reply(
        seller_slug="urban_thread",
        message="Hi, how much is the cotton kurti?",
        db_path=smoke_db,
        log=False,
    )
    assert draft.reply
    assert draft.language in ("en", "hi", "mr", "hinglish")
    assert isinstance(draft.needs_check, bool)
