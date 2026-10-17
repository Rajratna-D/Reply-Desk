"""Smoke test calling Ollama, automatically skipped if Ollama is not running."""

import json
import os
from pathlib import Path
import pytest
from engine.config import load_settings, validate_ollama_url
from engine.db import connect, init_db
from engine.importer import import_config
from engine.llm import ollama_status
from engine.service import draft_reply, select_gemma_model

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


def test_select_gemma_model_routing():
    # 1. Standard FAQ lookup: simple question, high retrieval count
    simple_route = select_gemma_model(
        query="Is the cotton kurti available in size L?",
        retrieved_chunks=["chunk1", "chunk2", "chunk3"],
        default_model="gemma2:2b",
    )
    assert simple_route["model"] == "gemma2:2b"
    assert simple_route["tier"] == "fast"
    assert simple_route["reason"] == "Standard FAQ lookup"

    # 2. Policy-sensitive keywords (refund, return, damaged, etc.) route to deep tier
    escalation_route = select_gemma_model(
        query="My parcel arrived damaged and I want an immediate refund or return",
        retrieved_chunks=["chunk1", "chunk2", "chunk3"],
        default_model="gemma2:2b",
    )
    assert escalation_route["model"] == "gemma2:9b"
    assert escalation_route["tier"] == "deep"
    assert "Complex or policy-sensitive" in escalation_route["reason"]

    # 3. Multi-part complexity (multiple question marks)
    multipart_route = select_gemma_model(
        query="What is the price? Can you deliver to Pune? Is COD available?",
        retrieved_chunks=["chunk1", "chunk2"],
        default_model="gemma2:2b",
    )
    assert multipart_route["model"] == "gemma2:9b"
    assert multipart_route["tier"] == "deep"

    # 4. Low retrieval confidence
    low_retrieval_route = select_gemma_model(
        query="Special embroidery inquiry",
        retrieved_chunks=["chunk1"],
        default_model="gemma2:2b",
    )
    assert low_retrieval_route["model"] == "gemma2:9b"
    assert low_retrieval_route["tier"] == "deep"

    # 5. Gemma 4 architecture routes to flagship tier
    gemma4_route = select_gemma_model(
        query="My parcel arrived damaged and I want an immediate refund",
        retrieved_chunks=["chunk1"],
        default_model="gemma4:e2b",
    )
    assert gemma4_route["model"] == "gemma4:e2b"
    assert gemma4_route["tier"] == "flagship"


def test_validate_ollama_url_ssrf():
    # Localhost and 127.0.0.1 allowed
    assert validate_ollama_url("http://localhost:11434") == "http://localhost:11434"
    assert validate_ollama_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert validate_ollama_url("localhost:11434") == "http://localhost:11434"
    assert validate_ollama_url("") == "http://localhost:11434"

    # Metadata and external IPs blocked
    with pytest.raises(ValueError, match="Blocked non-local Ollama host"):
        validate_ollama_url("http://169.254.169.254/latest/meta-data")

    with pytest.raises(ValueError, match="Blocked non-local Ollama host"):
        validate_ollama_url("http://metadata.google.internal")

    with pytest.raises(ValueError, match="Blocked non-local Ollama host"):
        validate_ollama_url("http://remote-server.evil.com:11434")


def test_draft_reply_force_model(smoke_db):
    """Test that force_model=True locks the target model even on escalation queries."""
    from unittest.mock import patch

    with patch("engine.service.generate_json") as mock_gen:
        mock_gen.return_value = {
            "reply": "We will issue a refund according to policy.",
            "language": "en",
            "needs_check": False,
            "reason": "",
            "_prompt_tokens": 100,
            "_output_tokens": 20,
        }

        # 1. Force gemma4:e2b
        draft_g4 = draft_reply(
            seller_slug="urban_thread",
            message="I demand an immediate refund for damaged item!",
            model="gemma4:e2b",
            db_path=smoke_db,
            log=False,
            force_model=True,
        )
        assert draft_g4.routed_model == "gemma4:e2b"
        assert "Forced single-model evaluation" in draft_g4.route_reason
        assert mock_gen.call_args[1]["model"] == "gemma4:e2b"

        # 2. Force gemma2:2b (would otherwise escalate to gemma2:9b on refund query)
        draft_2b = draft_reply(
            seller_slug="urban_thread",
            message="I demand an immediate refund for damaged item!",
            model="gemma2:2b",
            db_path=smoke_db,
            log=False,
            force_model=True,
        )
        assert draft_2b.routed_model == "gemma2:2b"
        assert "Forced single-model evaluation" in draft_2b.route_reason
        assert mock_gen.call_args[1]["model"] == "gemma2:2b"

        # 3. Dynamic routing without force_model (base gemma2:2b) escalates to gemma2:9b on refund
        draft_auto = draft_reply(
            seller_slug="urban_thread",
            message="I demand an immediate refund for damaged item!",
            model="gemma2:2b",
            db_path=smoke_db,
            log=False,
            force_model=False,
        )
        assert draft_auto.routed_model == "gemma2:9b"
        assert mock_gen.call_args[1]["model"] == "gemma2:9b"

