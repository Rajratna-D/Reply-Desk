"""Core service orchestration for drafting customer replies in ReplyDesk."""

import re
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

from engine.config import load_settings
from engine.db import connect, get_seller_by_slug, log_reply
from engine.guardrails import (
    detect_prompt_injection,
    redact_pii,
    risk_topics,
    ungrounded_amounts,
    verify_numeric_grounding,
)
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
    routed_model: str | None = None
    actual_model: str | None = None
    fallback_used: bool = False
    route_reason: str = ""
    retrieval_mode: str = "fts5_bm25"
    unverified_numbers: list[str] = field(default_factory=list)
    needs_human_review: bool | None = None
    would_route_to: str | None = None
    grounding_status: str | None = None
    triage_badge: str | None = None

    def __post_init__(self) -> None:
        if self.needs_human_review is None:
            self.needs_human_review = self.needs_check
        if self.routed_model is None:
            self.routed_model = self.model
        if self.actual_model is None:
            self.actual_model = self.model


# Escalation terms that require deeper reasoning or human review
POLICY_ESCALATION_TERMS = {
    "refund",
    "return",
    "damaged",
    "broken",
    "crushed",
    "cancel",
    "complaint",
    "wrong",
    "missing",
    "urgent",
    "exception",
    "late",
    "dispute",
}
POLICY_ESCALATION_REGEX = re.compile(
    r"\b(" + "|".join(sorted(POLICY_ESCALATION_TERMS, key=len, reverse=True)) + r")\w*",
    re.IGNORECASE,
)


def select_gemma_model(
    query: str,
    retrieved_chunks: list[Any],
    default_model: str = "gemma2:2b",
) -> dict[str, Any]:
    """Select appropriate Gemma model tier based on query complexity and policy sensitivity.

    Returns:
        dict with keys: 'model', 'tier', 'reason'.
    """
    if default_model.startswith("gemma4"):
        return {
            "model": default_model,
            "tier": "flagship",
            "reason": "Gemma 4 flagship architecture active",
        }

    has_escalation = bool(POLICY_ESCALATION_REGEX.search(query))
    has_multipart = query.count("?") > 1
    has_long_query = len(query.split()) > 35
    has_low_retrieval = len(retrieved_chunks) <= 1

    if has_escalation or has_multipart or has_long_query or has_low_retrieval:
        return {
            "model": "gemma2:9b",
            "tier": "deep",
            "reason": "Complex or policy-sensitive query",
        }

    return {
        "model": default_model,
        "tier": "fast",
        "reason": "Standard FAQ lookup",
    }


def draft_reply(
    seller_slug: str,
    message: str,
    *,
    model: str | None = None,
    log: bool = True,
    db_path: str | None = None,
    seller_action: str | None = None,
    conn: sqlite3.Connection | None = None,
    tone_override: str | None = None,
    force_model: bool = False,
    prior_queries: list[str] | None = None,
) -> Draft:
    """Orchestrate drafting a reply for a seller.

    Steps:
    1. Connect to SQLite (or reuse passed connection) and fetch seller.
    2. Scrub customer message for PII and check for indirect prompt injections.
    3. Build prompt context (shop details, catalogue, policies, style samples, known amounts).
    4. Route model dynamically (gemma2:2b vs gemma2:9b) with automatic local fallback.
    5. Generate structured JSON reply using Ollama.
    6. Run guardrails (numeric price grounding, numeric policy verification, risk topic alerts).
    7. Log reply to database (if log=True) and return Draft.

    NOTE: The app only drafts: it never sends messages automatically.
    """
    settings = load_settings(model_name=model, db_path=db_path)

    should_close = False
    if conn is None:
        conn = connect(settings.db_path)
        should_close = True

    try:
        seller = get_seller_by_slug(conn, seller_slug)
        if not seller:
            raise ValueError(f"Seller with slug '{seller_slug}' not found.")

        seller_id = seller["id"]

        # Step 1: PII Scrubbing
        scrubbed_message, _pii_detected = redact_pii(message)

        # Step 2: Indirect prompt injection check
        is_injection, injection_reason = detect_prompt_injection(scrubbed_message)
        if is_injection:
            safe_refusal = (
                "Thank you for reaching out. Your request has been forwarded to our team "
                "for personal review. A representative will get back to you shortly."
            )
            reply_id = None
            if log:
                reply_id = log_reply(
                    conn=conn,
                    seller_id=seller_id,
                    customer_message=scrubbed_message,
                    drafted_reply=safe_refusal,
                    model="system",
                    detected_language="en",
                    needs_check=True,
                    check_reason=injection_reason,
                    ungrounded_amounts=[],
                    risk_topics=["prompt_injection"],
                    latency_ms=0,
                    seller_action=seller_action,
                    routed_model="system",
                    retrieval_mode="blocked",
                    grounding_status="blocked",
                    triage_badge="NEEDS HUMAN",
                )
            return Draft(
                reply=safe_refusal,
                language="en",
                needs_check=True,
                reason=injection_reason,
                ungrounded_amounts=[],
                risk_topics=["prompt_injection"],
                model="system",
                latency_ms=0,
                reply_id=reply_id,
                routed_model="system",
                actual_model="system",
                fallback_used=False,
                route_reason="Prompt injection blocked",
                retrieval_mode="blocked",
                unverified_numbers=[],
                needs_human_review=True,
                would_route_to="system",
                grounding_status="blocked",
                triage_badge="NEEDS HUMAN",
            )

        # Step 3: Build context from database
        ctx = build_context(conn, seller_id, scrubbed_message, prior_queries=prior_queries)
        if not ctx.catalogue_block or not ctx.policies_block:
            raise ValueError("Seller must have at least one product and one policy before drafting.")

        messages = build_messages(ctx, scrubbed_message, tone_override=tone_override)

        # Step 4: Model routing and automatic fallback
        candidate_default = model or settings.model_name
        route_info = select_gemma_model(
            query=scrubbed_message,
            retrieved_chunks=ctx.retrieved_products,
            default_model=candidate_default,
        )
        would_route_to = route_info["model"]
        if force_model:
            target_model = model if model is not None else settings.model_name
            route_reason = f"Forced single-model evaluation: {target_model} (would route to: {would_route_to})"
        else:
            target_model = route_info["model"]
            route_reason = route_info["reason"]

        fallback_model = settings.model_name

        # Step 5: Call local LLM with fallback
        start_time = time.perf_counter()
        raw_result = generate_json(
            messages=messages,
            schema=RESPONSE_SCHEMA,
            model=target_model,
            fallback_model=fallback_model,
            host=settings.ollama_host,
            num_ctx=settings.num_ctx,
            temperature=settings.temperature,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        reply_text = str(raw_result.get("reply", "")).strip()
        lang = str(raw_result.get("language", "en")).strip()
        needs_check = bool(raw_result.get("needs_check", False))
        reason = str(raw_result.get("reason", "")).strip()

        actual_model = str(raw_result.get("actual_model", target_model))
        fallback_used = bool(raw_result.get("fallback_used", False))

        # Step 6: Guardrails
        # Verify numeric currency amounts
        un_amounts = ungrounded_amounts(reply_text, ctx.known_amounts)
        r_topics = risk_topics(scrubbed_message)

        if un_amounts:
            needs_check = True
            un_str = ", ".join(f"₹{a}" for a in un_amounts)
            grounding_note = f"Contains ungrounded price(s) not in seller data: {un_str}."
            reason = f"{grounding_note} {reason}".strip()

        # Verify numeric claims against retrieved catalogue and policies
        source_context = f"{ctx.catalogue_block}\n{ctx.policies_block}"
        numeric_verification = verify_numeric_grounding(
            reply_text,
            source_context,
            customer_query=scrubbed_message,
        )
        unverified_numbers = numeric_verification.get("unverified_numbers", [])
        if not numeric_verification.get("is_grounded", True):
            needs_check = True
            unv_str = ", ".join(unverified_numbers)
            num_note = f"Contains ungrounded numeric claim(s) not in seller data: {unv_str}."
            reason = f"{num_note} {reason}".strip()

        if "private_and_sensitive" in r_topics:
            needs_check = True
            security_note = "Private, sensitive, or prompt injection inquiry detected."
            reason = f"{security_note} {reason}".strip()

        # Telemetry resolution
        grounding_status = "verified"
        if un_amounts or not numeric_verification.get("is_grounded", True) or unverified_numbers:
            grounding_status = "unverified"

        cust_msg_lower = scrubbed_message.lower()
        if "prompt_injection" in r_topics or is_injection:
            triage_badge = "NEEDS HUMAN"
        elif un_amounts or not numeric_verification.get("is_grounded", True) or "private_and_sensitive" in r_topics:
            triage_badge = "NEEDS HUMAN"
        elif target_model == "gemma2:9b" or any(w in cust_msg_lower for w in POLICY_ESCALATION_TERMS):
            triage_badge = "POLICY CHECK"
        else:
            triage_badge = "AUTO-DRAFT READY"

        reply_id = None
        if log:
            reply_id = log_reply(
                conn=conn,
                seller_id=seller_id,
                customer_message=scrubbed_message,
                drafted_reply=reply_text,
                model=actual_model,
                detected_language=lang,
                needs_check=needs_check,
                check_reason=reason,
                ungrounded_amounts=un_amounts,
                risk_topics=r_topics,
                latency_ms=latency_ms,
                seller_action=seller_action,
                routed_model=target_model,
                retrieval_mode=ctx.retrieval_mode,
                grounding_status=grounding_status,
                triage_badge=triage_badge,
            )

        return Draft(
            reply=reply_text,
            language=lang,
            needs_check=needs_check,
            reason=reason,
            ungrounded_amounts=un_amounts,
            risk_topics=r_topics,
            model=actual_model,
            latency_ms=latency_ms,
            reply_id=reply_id,
            prompt_tokens=raw_result.get("_prompt_tokens"),
            output_tokens=raw_result.get("_output_tokens"),
            routed_model=target_model,
            actual_model=actual_model,
            fallback_used=fallback_used,
            route_reason=route_reason,
            retrieval_mode=ctx.retrieval_mode,
            unverified_numbers=unverified_numbers,
            needs_human_review=needs_check,
            would_route_to=would_route_to,
            grounding_status=grounding_status,
            triage_badge=triage_badge,
        )
    finally:
        if should_close:
            conn.close()
