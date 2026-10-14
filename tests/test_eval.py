"""Tests for evaluation scoring, normalization, and database recording."""

import pytest
from engine.db import connect, create_eval_run, finish_eval_run, get_eval_results, init_db, list_eval_runs, record_eval_result
from engine.service import Draft
from eval.run_eval import normalize_for_facts, score_reply


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_eval.db"
    init_db(str(db_file))
    return str(db_file)


def test_normalize_for_facts():
    # Number with comma
    assert normalize_for_facts("Total price is ₹1,499.") == "total price is ₹1499."
    # Devanagari numerals
    assert normalize_for_facts("किंमत ₹१,२०० आहे") == "किंमत ₹1200 आहे"
    # En dash range normalization
    assert normalize_for_facts("1\u20132 days") == "1-2 days"


def test_score_reply_facts_and_needs_check():
    case = {
        "id": "TEST-01",
        "language": "en",
        "must_include": [["899"], ["blue", "mustard"]],
        "must_not_include": ["discount", "free"],
        "expect_needs_check": False,
    }

    # Perfect pass
    valid_draft = Draft(
        reply="The cotton kurti is ₹899 in blue color.",
        language="en",
        needs_check=False,
        reason="",
        ungrounded_amounts=[],
        risk_topics=[],
        model="test-model",
        latency_ms=1500,
    )
    scores = score_reply(case, valid_draft)
    assert scores["facts_ok"] is True
    assert scores["needs_check_ok"] is True
    assert scores["language_ok"] is True
    assert scores["passed"] is True

    # Missing required alternative (no blue or mustard)
    missing_draft = Draft(
        reply="The cotton kurti is ₹899 in red color.",
        language="en",
        needs_check=False,
        reason="",
        ungrounded_amounts=[],
        risk_topics=[],
        model="test-model",
        latency_ms=1500,
    )
    scores_missing = score_reply(case, missing_draft)
    assert scores_missing["facts_ok"] is False
    assert scores_missing["passed"] is False

    # Forbidden word present
    forbidden_draft = Draft(
        reply="The cotton kurti is ₹899 with free delivery.",
        language="en",
        needs_check=False,
        reason="",
        ungrounded_amounts=[],
        risk_topics=[],
        model="test-model",
        latency_ms=1500,
    )
    scores_forbidden = score_reply(case, forbidden_draft)
    assert scores_forbidden["facts_ok"] is False
    assert "free" in scores_forbidden["forbidden_found"]
    assert scores_forbidden["passed"] is False


def test_score_reply_language_script():
    hi_case = {
        "id": "TEST-HI",
        "language": "hi",
        "must_include": [["नहीं"]],
        "must_not_include": [],
        "expect_needs_check": False,
    }

    # Valid Devanagari Hindi
    dev_draft = Draft(
        reply="कैश ऑन डिलीवरी उपलब्ध नहीं है।",
        language="hi",
        needs_check=False,
        reason="",
        ungrounded_amounts=[],
        risk_topics=[],
        model="test-model",
        latency_ms=1500,
    )
    assert score_reply(hi_case, dev_draft)["language_ok"] is True

    # Latin response to Hindi question fails script check
    latin_draft = Draft(
        reply="Sorry, COD is not available nahi.",
        language="hi",
        needs_check=False,
        reason="",
        ungrounded_amounts=[],
        risk_topics=[],
        model="test-model",
        latency_ms=1500,
    )
    assert score_reply(hi_case, latin_draft)["language_ok"] is False


def test_eval_database_logging(temp_db):
    conn = connect(temp_db)
    run_id = create_eval_run(conn, model="gemma2:2b", notes="Automated test run")
    assert run_id > 0

    record_eval_result(
        conn=conn,
        run_id=run_id,
        case_id="UT-01",
        shop_slug="urban_thread",
        language="en",
        category="price",
        split="dev",
        reply="Kurti is ₹899.",
        needs_check=False,
        facts_ok=True,
        needs_check_ok=True,
        language_ok=True,
        language_label_ok=True,
        latency_ms=3200,
        prompt_tokens=450,
        output_tokens=32,
    )

    finish_eval_run(conn, run_id)

    runs = list_eval_runs(conn)
    assert len(runs) == 1
    assert runs[0]["model"] == "gemma2:2b"
    assert runs[0]["total_cases"] == 1
    assert runs[0]["passed_total"] == 1

    results = get_eval_results(conn, run_id)
    assert len(results) == 1
    assert results[0]["case_id"] == "UT-01"
    assert results[0]["prompt_tokens"] == 450
    assert results[0]["output_tokens"] == 32
    conn.close()
