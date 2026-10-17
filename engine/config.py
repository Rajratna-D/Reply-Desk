"""Configuration settings for ReplyDesk."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Automatically load .env if present
load_dotenv()


@dataclass(frozen=True)
class Settings:
    model_name: str
    ollama_host: str = "http://localhost:11434"
    num_ctx: int = 4096
    db_path: str = "data/replydesk.db"
    temperature: float = 0.2


def _parse_int(raw: object, default: int) -> int:
    """Parse integer safely, tolerating inline comments, whitespace, and empty strings."""
    if raw is None:
        return default
    try:
        cleaned = str(raw).split("#")[0].strip()
        return int(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default


def _parse_float(raw: object, default: float) -> float:
    """Parse float safely, tolerating inline comments, whitespace, and empty strings."""
    if raw is None:
        return default
    try:
        cleaned = str(raw).split("#")[0].strip()
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default


import urllib.parse

ALLOWED_OLLAMA_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def validate_ollama_url(url: str) -> str:
    """Validate Ollama host URL to prevent SSRF and external egress.

    Allows only localhost, 127.0.0.1, or 0.0.0.0 HTTP/HTTPS URLs by default.
    Set ALLOW_REMOTE_OLLAMA=true in environment to unlock remote hosts.
    """
    if not url or not url.strip():
        return "http://localhost:11434"

    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "http://" + cleaned

    parsed = urllib.parse.urlparse(cleaned)
    hostname = (parsed.hostname or "").lower()

    allow_remote = os.getenv("ALLOW_REMOTE_OLLAMA", "false").lower() in ("true", "1", "yes")

    if not allow_remote:
        if hostname in ("169.254.169.254", "metadata.google.internal") or hostname not in ALLOWED_OLLAMA_HOSTS:
            raise ValueError(
                f"Blocked non-local Ollama host '{hostname}'. For local privacy and offline safety, "
                "only localhost and 127.0.0.1 are permitted."
            )

    return cleaned


def load_settings(
    *,
    model_name: str | None = None,
    ollama_host: str | None = None,
    num_ctx: int | None = None,
    db_path: str | None = None,
    temperature: float | None = None,
) -> Settings:
    """Load settings from environment variables or explicit overrides.

    Raises:
        ValueError: If MODEL_NAME is not set.
    """
    resolved_model = model_name or os.getenv("MODEL_NAME")
    if not resolved_model or not resolved_model.strip():
        raise ValueError(
            "MODEL_NAME is not set. Please set MODEL_NAME in your environment or .env file "
            "(e.g. MODEL_NAME=gemma2:2b). See docs/SETUP.md for instructions."
        )

    raw_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    resolved_host = validate_ollama_url(raw_host)
    resolved_num_ctx = num_ctx if num_ctx is not None else _parse_int(os.getenv("NUM_CTX"), 4096)
    resolved_db_path = db_path or os.getenv("DB_PATH", "data/replydesk.db")
    resolved_temp = temperature if temperature is not None else _parse_float(os.getenv("TEMPERATURE"), 0.2)

    return Settings(
        model_name=resolved_model.strip(),
        ollama_host=resolved_host.strip(),
        num_ctx=resolved_num_ctx,
        db_path=resolved_db_path.strip(),
        temperature=resolved_temp,
    )
