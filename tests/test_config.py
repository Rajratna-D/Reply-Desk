"""Tests for engine/config.py."""

import os
import pytest
from engine.config import load_settings


def test_missing_model_name_raises_clear_error(monkeypatch):
    monkeypatch.delenv("MODEL_NAME", raising=False)
    with pytest.raises(ValueError) as excinfo:
        load_settings(model_name="")
    assert "MODEL_NAME is not set" in str(excinfo.value)
    assert "See docs/SETUP.md" in str(excinfo.value)


def test_valid_model_name(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "gemma2:2b")
    settings = load_settings()
    assert settings.model_name == "gemma2:2b"
    assert settings.ollama_host == "http://localhost:11434"
    assert settings.num_ctx == 4096
