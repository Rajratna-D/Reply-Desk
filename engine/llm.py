"""Ollama client integration with structured output and robust error handling."""

import json
import logging
import re
from typing import Any
import ollama

logger = logging.getLogger(__name__)


class OllamaUnavailable(Exception):
    """Raised when Ollama server cannot be reached."""


class ModelMissing(Exception):
    """Raised when the requested model is not downloaded or found in Ollama."""


class BadModelOutput(Exception):
    """Raised when the model output cannot be parsed as the required JSON schema."""


def ollama_status(host: str = "http://localhost:11434") -> dict[str, Any]:
    """Check connectivity to Ollama server and list available models."""
    try:
        client = ollama.Client(host=host)
        resp = client.list()
        # resp can be a ListResponse or dict containing 'models'
        models_raw = getattr(resp, "models", None) or resp.get("models", [])
        model_names = []
        for m in models_raw:
            if hasattr(m, "model"):
                model_names.append(m.model)
            elif isinstance(m, dict) and "name" in m:
                model_names.append(m["name"])
            elif isinstance(m, dict) and "model" in m:
                model_names.append(m["model"])
            else:
                model_names.append(str(m))

        return {
            "reachable": True,
            "models": model_names,
            "error": None,
        }
    except Exception as e:
        return {
            "reachable": False,
            "models": [],
            "error": str(e),
        }


def _clean_json_markdown(text: str) -> str:
    """Strip markdown code fence if the model wrapped JSON in ```json ... ```."""
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
        if match:
            return match.group(1).strip()
    return stripped


def generate_json(
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    *,
    model: str,
    host: str = "http://localhost:11434",
    num_ctx: int = 4096,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Call Ollama chat API requesting structured JSON output with fallback and one retry.

    Returns:
        Parsed dict matching schema.
    Raises:
        OllamaUnavailable: If Ollama cannot be reached.
        ModelMissing: If model is not found in Ollama.
        BadModelOutput: If output is not valid JSON after retry.
    """
    client = ollama.Client(host=host)
    options = {
        "num_ctx": num_ctx,
        "temperature": temperature,
    }

    # Attempt 1: Try with format=schema (structured outputs)
    use_schema_format = True
    raw_content = ""
    last_prompt_tokens: int | None = None
    last_output_tokens: int | None = None

    def _call(msgs: list[dict[str, str]], fmt: Any) -> str:
        nonlocal use_schema_format, last_prompt_tokens, last_output_tokens
        try:
            res = client.chat(
                model=model,
                messages=msgs,
                format=fmt,
                options=options,
            )
            last_prompt_tokens = getattr(res, "prompt_eval_count", None) or (res.get("prompt_eval_count") if isinstance(res, dict) else None)
            last_output_tokens = getattr(res, "eval_count", None) or (res.get("eval_count") if isinstance(res, dict) else None)
            return getattr(res.message, "content", "") if hasattr(res, "message") else res["message"]["content"]
        except Exception as ex:
            err_msg = str(ex).lower()
            if "connection refused" in err_msg or "connect" in err_msg or "unavailable" in err_msg:
                raise OllamaUnavailable(
                    f"Cannot connect to Ollama at {host}. Please verify that 'ollama serve' is running."
                ) from ex
            if "not found" in err_msg or "404" in err_msg:
                raise ModelMissing(
                    f"Model '{model}' is not found in Ollama. Please run: ollama pull {model}"
                ) from ex

            # If format=schema was rejected by this Ollama version, fall back to format='json'
            if use_schema_format and fmt != "json":
                logger.info("Structured output schema rejected; falling back to format='json'")
                use_schema_format = False
                res = client.chat(
                    model=model,
                    messages=msgs,
                    format="json",
                    options=options,
                )
                last_prompt_tokens = getattr(res, "prompt_eval_count", None) or (res.get("prompt_eval_count") if isinstance(res, dict) else None)
                last_output_tokens = getattr(res, "eval_count", None) or (res.get("eval_count") if isinstance(res, dict) else None)
                return getattr(res.message, "content", "") if hasattr(res, "message") else res["message"]["content"]
            raise

    try:
        raw_content = _call(messages, schema if use_schema_format else "json")
    except (OllamaUnavailable, ModelMissing):
        raise
    except Exception as e:
        raise BadModelOutput(f"Ollama call failed: {e}") from e

    # Parse JSON
    cleaned = _clean_json_markdown(raw_content)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "reply" in parsed:
            parsed["_prompt_tokens"] = last_prompt_tokens
            parsed["_output_tokens"] = last_output_tokens
            return parsed
    except json.JSONDecodeError:
        pass

    # Attempt 2 (Retry once): Prompt model to fix JSON
    logger.warning("First attempt returned invalid JSON. Retrying with correction prompt...")
    retry_messages = list(messages)
    retry_messages.append({"role": "assistant", "content": raw_content})
    retry_messages.append(
        {
            "role": "user",
            "content": "Your previous response was not valid JSON matching the schema. "
            "Please return ONLY a valid JSON object matching the required schema with keys: "
            "'reply', 'language', 'needs_check', and 'reason'.",
        }
    )

    try:
        raw_content = _call(retry_messages, "json")
        cleaned = _clean_json_markdown(raw_content)
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "reply" in parsed:
            parsed["_prompt_tokens"] = last_prompt_tokens
            parsed["_output_tokens"] = last_output_tokens
            return parsed
    except (OllamaUnavailable, ModelMissing):
        raise
    except Exception as e:
        raise BadModelOutput(
            f"Model returned invalid JSON after retry: {raw_content}. Error: {e}"
        ) from e

    raise BadModelOutput(f"Model returned invalid JSON after retry: {raw_content}")
