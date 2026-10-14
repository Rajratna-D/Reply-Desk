"""Core service orchestration for drafting customer replies in ReplyDesk."""

import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from engine.config import load_settings
from engine.db import connect, get_seller_by_slug, log_reply
from engine.guardrails import risk_topics, ungrounded_amounts
from engine.llm import generate_json
from engine.prompt import RESPONSE_SCHEMA, build_messages
from engine.retrieval import build_context


@dataclass
class Draft:
    reply: str
    language: str
    needs_check: bool
    reason: str
    ungrounded_amounts: list[int]
    risk_topics: list[str]
    model: str
    latency_ms: int
    reply_id: int | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None


def draft_reply(
    seller_slug: str,
    message: str,
    *,
    model: str | None = None,
    log: bool = True,
    db_path: str | None = None,
    seller_action: str | None = None,
) -> Draft:
    """Orchestrate drafting a reply for a seller.

    Steps:
    1. Connect to SQLite and fetch seller.
    2. Build prompt context (shop details, catalogue, policies, style samples, known amounts).
    3. Generate structured JSON reply using Ollama.
    4. Run guardrails (numeric price grounding, risk topic alerts).
    5. Log reply to database (if log=True) and return Draft.

    NOTE: The app only drafts; it never sends messages automatically.
    """
    settings = load_settings(model_name=model, db_path=db_path)
    active_model = settings.model_name

    conn = connect(settings.db_path)
    try:
        seller = get_seller_by_slug(conn, seller_slug)
        if not seller:
            raise ValueError(f"Seller with slug '{seller_slug}' not found.")

        seller_id = seller["id"]

        # Build context from database
        ctx = build_context(conn, seller_id, message)
        if not ctx.catalogue_block or not ctx.policies_block:
            raise ValueError("Seller must have at least one product and one policy before drafting.")

        messages = build_messages(ctx, message)

        # Call local LLM
        start_time = time.perf_counter()
        raw_result = generate_json(
            messages=messages,
            schema=RESPONSE_SCHEMA,
            model=active_model,
            host=settings.ollama_host,
            num_ctx=settings.num_ctx,
            temperature=settings.temperature,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        reply_text = str(raw_result.get("reply", "")).strip()
        lang = str(raw_result.get("language", "en")).strip()
        needs_check = bool(raw_result.get("needs_check", False))
        reason = str(raw_result.get("reason", "")).strip()

        # Guardrails: verify numeric currency amounts
        un_amounts = ungrounded_amounts(reply_text, ctx.known_amounts)
        r_topics = risk_topics(message)

        if un_amounts:
            needs_check = True
            un_str = ", ".join(f"₹{a}" for a in un_amounts)
            grounding_note = f"Contains ungrounded price(s) not in seller data: {un_str}."
            reason = f"{grounding_note} {reason}".strip()

        reply_id = None
        if log:
            reply_id = log_reply(
                conn=conn,
                seller_id=seller_id,
                customer_message=message,
                drafted_reply=reply_text,
                model=active_model,
                detected_language=lang,
                needs_check=needs_check,
                check_reason=reason,
                ungrounded_amounts=un_amounts,
                risk_topics=r_topics,
                latency_ms=latency_ms,
                seller_action=seller_action,
            )

        return Draft(
            reply=reply_text,
            language=lang,
            needs_check=needs_check,
            reason=reason,
            ungrounded_amounts=un_amounts,
            risk_topics=r_topics,
            model=active_model,
            latency_ms=latency_ms,
            reply_id=reply_id,
            prompt_tokens=raw_result.get("_prompt_tokens"),
            output_tokens=raw_result.get("_output_tokens"),
        )
    finally:
        conn.close()
