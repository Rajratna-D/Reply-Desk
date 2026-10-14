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


def test_resilient_num_ctx_and_temperature(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "gemma2:2b")
    # Inline comments in environment variables
    monkeypatch.setenv("NUM_CTX", "8192 # large context")
    monkeypatch.setenv("TEMPERATURE", "0.5 # slightly creative")
    settings = load_settings()
    assert settings.num_ctx == 8192
    assert settings.temperature == 0.5

    # Invalid / empty fallback
    monkeypatch.setenv("NUM_CTX", "invalid_number")
    monkeypatch.setenv("TEMPERATURE", "")
    fallback_settings = load_settings()
    assert fallback_settings.num_ctx == 4096
    assert fallback_settings.temperature == 0.2
