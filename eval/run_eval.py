"""Evaluation runner for ReplyDesk.

Executes test cases from eval/questions.json, calculates facts_ok,
needs_check_ok, language_ok, records results in SQLite, and generates
markdown reports.

CLI usage:
    python -m eval.run_eval [--model gemma2:2b] [--split dev|test|all] [--notes "..."]
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Force UTF-8 encoding for console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import load_settings
from engine.db import (
    connect,
    create_eval_run,
    finish_eval_run,
    get_seller_by_slug,
    record_eval_result,
)
from engine.guardrails import normalize_digits
from engine.importer import import_config
from engine.service import Draft, draft_reply

QUESTIONS_PATH = PROJECT_ROOT / "eval" / "questions.json"
REPORTS_DIR = PROJECT_ROOT / "eval" / "reports"
CONFIG_DIR = PROJECT_ROOT / "config"


def normalize_for_facts(text: str) -> str:
    """Normalize text for factual string matching.

    Converts Devanagari digits to ASCII, removes commas within numbers,
    and lowercases the text.
    """
    t = normalize_digits(text)
    # Remove commas between digits e.g. 1,200 -> 1200
    t = re.sub(r"(\d),(\d)", r"\1\2", t)
    # Normalize en dashes, em dashes, or hyphens in ranges
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    return t.lower()


def score_reply(case: dict[str, Any], draft: Draft) -> dict[str, Any]:
    """Score a single drafted reply against ground truth expectations."""
    norm_reply = normalize_for_facts(draft.reply)

    # 1. facts_ok check
    must_include = case.get("must_include", [])
    must_not_include = case.get("must_not_include", [])

    facts_ok = True
    missing_groups = []

    for group in must_include:
        group_matched = False
        for alt in group:
            norm_alt = normalize_for_facts(str(alt))
            if norm_alt.isdigit():
                if re.search(r"(?<!\d)" + re.escape(norm_alt) + r"(?!\d)", norm_reply):
                    group_matched = True
                    break
            else:
                if norm_alt in norm_reply:
                    group_matched = True
                    break
        if not group_matched:
            facts_ok = False
            missing_groups.append(group)

    forbidden_found = []
    for forbidden in must_not_include:
        norm_forbidden = normalize_for_facts(str(forbidden))
        if norm_forbidden.isdigit():
            if re.search(r"(?<!\d)" + re.escape(norm_forbidden) + r"(?!\d)", norm_reply):
                facts_ok = False
                forbidden_found.append(forbidden)
        else:
            if norm_forbidden in norm_reply:
                facts_ok = False
                forbidden_found.append(forbidden)

    # 2. needs_check_ok check
    expect_check = bool(case.get("expect_needs_check", False))
    needs_check_ok = (draft.needs_check == expect_check)

    # 3. language_ok check (script check)
    exp_lang = case.get("language", "en").lower()
    dev_count = sum(1 for c in draft.reply if 0x0900 <= ord(c) <= 0x097F)
    latin_count = sum(1 for c in draft.reply if c.isascii() and c.isalpha())
    total_letters = dev_count + latin_count

    if exp_lang in ("en", "hinglish"):
        # English and Hinglish should be written in Latin script (zero Devanagari)
        language_ok = (dev_count == 0)
    elif exp_lang in ("hi", "mr"):
        # Hindi and Marathi must use Devanagari script for >= 50% of letters
        language_ok = (dev_count / total_letters >= 0.5) if total_letters > 0 else False
    else:
        language_ok = True

    # 4. language_label_ok (whether the model labeled language correctly)
    language_label_ok = (draft.language.lower() == exp_lang)

    # 5. numeric_grounding_ok (no unverified numbers or ungrounded currency amounts)
    numeric_grounding_ok = (len(draft.unverified_numbers) == 0 and len(draft.ungrounded_amounts) == 0)

    # 6. overall pass
    passed = bool(facts_ok and needs_check_ok and language_ok)

    return {
        "facts_ok": facts_ok,
        "missing_groups": missing_groups,
        "forbidden_found": forbidden_found,
        "needs_check_ok": needs_check_ok,
        "language_ok": language_ok,
        "language_label_ok": language_label_ok,
        "numeric_grounding_ok": numeric_grounding_ok,
        "retrieval_mode": draft.retrieval_mode,
        "passed": passed,
    }


def ensure_sample_shops(conn) -> None:
    """Ensure the 3 sample shops are populated in the database."""
    sample_files = ["urban_thread.json", "sweet_crumbs.json", "kalakruti_jewels.json"]
    for fname in sample_files:
        fpath = CONFIG_DIR / fname
        if not fpath.exists():
            continue
        slug = fname.replace(".json", "")
        if not get_seller_by_slug(conn, slug):
            data = json.loads(fpath.read_text(encoding="utf-8"))
            import_config(conn, data, replace=True)


def run_evaluation(
    model: str | None = None,
    split_filter: str = "all",
    notes: str | None = None,
    progress_callback: Any = None,
) -> dict[str, Any]:
    """Execute evaluation cases and record run in database.

    Returns:
        Dictionary with run_id, model, summary metrics, and case results.
    """
    settings = load_settings(model_name=model)
    active_model = settings.model_name

    conn = connect(settings.db_path)
    try:
        ensure_sample_shops(conn)

        if not QUESTIONS_PATH.exists():
            raise FileNotFoundError(f"Questions file not found at {QUESTIONS_PATH}")

        all_cases = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

        if split_filter in ("dev", "test"):
            cases = [c for c in all_cases if c.get("split") == split_filter]
        else:
            cases = all_cases

        run_id = create_eval_run(conn, model=active_model, notes=notes)

        results = []
        total = len(cases)

        for idx, case in enumerate(cases):
            case_id = case["id"]
            shop_slug = case["shop"]
            message = case["message"]

            if progress_callback:
                progress_callback(idx, total, case)

            # Generate draft with force_model=True for pure single-model benchmarking
            try:
                draft = draft_reply(
                    seller_slug=shop_slug,
                    message=message,
                    model=active_model,
                    log=False,
                    conn=conn,
                    force_model=True,
                )
            except Exception as ex:
                # Handle generation failure gracefully
                draft = Draft(
                    reply=f"ERROR: {ex}",
                    language="en",
                    needs_check=True,
                    reason=str(ex),
                    ungrounded_amounts=[],
                    risk_topics=[],
                    model=active_model,
                    latency_ms=0,
                )

            scores = score_reply(case, draft)

            # Record result in database
            record_eval_result(
                conn=conn,
                run_id=run_id,
                case_id=case_id,
                shop_slug=shop_slug,
                language=case["language"],
                category=case.get("category", "general"),
                split=case.get("split"),
                reply=draft.reply,
                needs_check=draft.needs_check,
                facts_ok=scores["facts_ok"],
                needs_check_ok=scores["needs_check_ok"],
                language_ok=scores["language_ok"],
                language_label_ok=scores["language_label_ok"],
                latency_ms=draft.latency_ms,
                prompt_tokens=draft.prompt_tokens,
                output_tokens=draft.output_tokens,
                numeric_grounding_ok=scores["numeric_grounding_ok"],
                retrieval_mode=draft.retrieval_mode,
            )

            results.append({
                "case": case,
                "draft": draft,
                "scores": scores,
            })

        finish_eval_run(conn, run_id)

        # Build summary slices
        slices = {
            "All": results,
            "English": [r for r in results if r["case"]["language"] == "en"],
            "Hindi": [r for r in results if r["case"]["language"] == "hi"],
            "Marathi": [r for r in results if r["case"]["language"] == "mr"],
            "Hinglish": [r for r in results if r["case"]["language"] == "hinglish"],
            "dev": [r for r in results if r["case"].get("split") == "dev"],
            "test": [r for r in results if r["case"].get("split") == "test"],
        }

        retrieval_counts: dict[str, int] = {}
        for r in results:
            mode = r["draft"].retrieval_mode or "unknown"
            retrieval_counts[mode] = retrieval_counts.get(mode, 0) + 1

        grounding_counts = {
            "verified": sum(1 for r in results if r["scores"]["numeric_grounding_ok"]),
            "unverified": sum(1 for r in results if not r["scores"]["numeric_grounding_ok"]),
        }

        slice_stats = {}
        for slice_name, slice_rows in slices.items():
            count = len(slice_rows)
            if count == 0:
                continue
            facts_passed = sum(1 for r in slice_rows if r["scores"]["facts_ok"])
            check_passed = sum(1 for r in slice_rows if r["scores"]["needs_check_ok"])
            lang_passed = sum(1 for r in slice_rows if r["scores"]["language_ok"])
            grounding_passed = sum(1 for r in slice_rows if r["scores"]["numeric_grounding_ok"])
            total_passed = sum(1 for r in slice_rows if r["scores"]["passed"])
            latencies = [r["draft"].latency_ms for r in slice_rows if r["draft"].latency_ms > 0]
            med_latency = statistics.median(latencies) if latencies else 0

            slice_stats[slice_name] = {
                "count": count,
                "facts_ok": f"{facts_passed}/{count} ({round(facts_passed/count*100, 1)}%)",
                "needs_check_ok": f"{check_passed}/{count} ({round(check_passed/count*100, 1)}%)",
                "language_ok": f"{lang_passed}/{count} ({round(lang_passed/count*100, 1)}%)",
                "numeric_grounding_ok": f"{grounding_passed}/{count} ({round(grounding_passed/count*100, 1)}%)",
                "passed": f"{total_passed}/{count} ({round(total_passed/count*100, 1)}%)",
                "median_latency_ms": int(med_latency),
                "pass_rate": round(total_passed / count * 100, 1),
            }

        summary_data = {
            "run_id": run_id,
            "model": active_model,
            "split": split_filter,
            "notes": notes or "",
            "total_cases": total,
            "overall_pass_rate": slice_stats.get("All", {}).get("pass_rate", 0.0),
            "retrieval_modes": retrieval_counts,
            "grounding_summary": grounding_counts,
            "slice_stats": slice_stats,
            "results": results,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Write markdown report
        generate_markdown_report(summary_data)

        return summary_data
    finally:
        conn.close()


def generate_markdown_report(summary: dict[str, Any]) -> str:
    """Generate and write a markdown evaluation report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    model_tag = summary["model"].replace(":", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"eval_{model_tag}_{timestamp}.md"
    latest_file = REPORTS_DIR / "latest_eval.md"

    retrieval_summary_str = ", ".join(f"{k}: {v}" for k, v in summary.get("retrieval_modes", {}).items()) or "None"
    grounding_summary = summary.get("grounding_summary", {})
    verified_grounding = grounding_summary.get("verified", 0)

    lines = [
        f"# ReplyDesk Evaluation Report - {summary['model']}",
        "",
        f"- **Date & Time:** {summary['timestamp']}",
        f"- **Model:** `{summary['model']}`",
        f"- **Split:** `{summary['split']}`",
        f"- **Notes:** {summary['notes'] or 'Standard automated benchmark run'}",
        f"- **Total Cases:** {summary['total_cases']}",
        f"- **Overall Pass Rate:** {summary['overall_pass_rate']}%",
        f"- **Retrieval Modes:** `{retrieval_summary_str}`",
        f"- **Numeric Grounding Verified:** {verified_grounding}/{summary['total_cases']}",
        "",
        "## Summary Results by Slice",
        "",
        "| Slice | Cases | facts_ok | needs_check_ok | language_ok | numeric_grounding | Overall Pass | Median Latency |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for slice_name, stats in summary["slice_stats"].items():
        lines.append(
            f"| {slice_name} | {stats['count']} | {stats['facts_ok']} | "
            f"{stats['needs_check_ok']} | {stats['language_ok']} | {stats.get('numeric_grounding_ok', 'N/A')} | "
            f"**{stats['passed']}** | {stats['median_latency_ms']} ms |"
        )

    lines.extend([
        "",
        "## Detailed Case Breakdown",
        "",
        "| ID | Shop | Lang | Cat | Split | Pass | Mode | Grounding | Latency | Customer Inquiry | Reply Draft | Diagnostic |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])

    for item in summary["results"]:
        c = item["case"]
        d = item["draft"]
        s = item["scores"]
        pass_badge = "PASS" if s["passed"] else "FAIL"
        clean_inquiry = c["message"].replace("|", "\\|")
        clean_reply = d.reply.replace("|", "\\|").replace("\n", " ")
        ground_badge = "VERIFIED" if s.get("numeric_grounding_ok", True) else "UNVERIFIED"
        mode_str = d.retrieval_mode or "unknown"
        diag = []
        if not s["facts_ok"]:
            if s["missing_groups"]:
                diag.append(f"Missing facts: {s['missing_groups']}")
            if s["forbidden_found"]:
                diag.append(f"Forbidden: {s['forbidden_found']}")
        if not s["needs_check_ok"]:
            diag.append(f"Check mismatch (got {d.needs_check}, exp {c.get('expect_needs_check')})")
        if not s["language_ok"]:
            diag.append("Script mismatch")

        diag_str = ", ".join(diag) if diag else "Clean"
        lines.append(
            f"| `{c['id']}` | {c['shop']} | {c['language']} | {c.get('category')} | {c.get('split')} | "
            f"**{pass_badge}** | `{mode_str}` | {ground_badge} | {d.latency_ms} ms | {clean_inquiry} | {clean_reply} | {diag_str} |"
        )

    lines.extend([
        "",
        "## Diagnostic Failures",
        "",
    ])

    failures = [r for r in summary["results"] if not r["scores"]["passed"]]
    if not failures:
        lines.append("No failures! 100% test cases passed cleanly.")
    else:
        for f in failures:
            c = f["case"]
            d = f["draft"]
            s = f["scores"]
            lines.append(f"### Case {c['id']} ({c['shop']} - {c['language']} - {c.get('category')})")
            lines.append(f"- **Message:** \"{c['message']}\"")
            lines.append(f"- **Draft:** \"{d.reply}\"")
            lines.append(f"- **Expected Needs Check:** {c.get('expect_needs_check')} (Got: {d.needs_check})")
            if s["missing_groups"]:
                lines.append(f"- **Missing Required Facts:** {s['missing_groups']}")
            if s["forbidden_found"]:
                lines.append(f"- **Forbidden Strings Found:** {s['forbidden_found']}")
            if not s["language_ok"]:
                lines.append("- **Language Script Issue:** Failed expected script distribution.")
            lines.append("")

    report_text = "\n".join(lines)
    report_file.write_text(report_text, encoding="utf-8")
    latest_file.write_text(report_text, encoding="utf-8")
    return str(report_file)


def main():
    parser = argparse.ArgumentParser(description="ReplyDesk Benchmark Evaluation Runner")
    parser.add_argument("--model", type=str, default=None, help="Ollama model tag to evaluate")
    parser.add_argument("--split", type=str, default="all", choices=["all", "dev", "test"], help="Dataset split")
    parser.add_argument("--notes", type=str, default="", help="Optional run notes")
    args = parser.parse_args()

    print("=" * 65)
    print("ReplyDesk Model Evaluation Runner (Milestone 3)")
    print("=" * 65)

    def print_progress(idx, total, case):
        print(f"[{idx+1:02d}/{total:02d}] Evaluating {case['id']} ({case['shop']} / {case['language']})...", flush=True)

    summary = run_evaluation(
        model=args.model,
        split_filter=args.split,
        notes=args.notes,
        progress_callback=print_progress,
    )

    print("\n" + "=" * 65)
    print(f"RESULTS FOR MODEL: {summary['model']}")
    print(f"Overall Pass Rate: {summary['overall_pass_rate']}% ({summary['total_cases']} cases)")
    print("=" * 65)
    print(f"{'Slice':<12} | {'Cases':<6} | {'Facts OK':<16} | {'Check OK':<16} | {'Pass':<16} | {'Med Latency'}")
    print("-" * 85)

    for slice_name, stats in summary["slice_stats"].items():
        print(
            f"{slice_name:<12} | {stats['count']:<6} | {stats['facts_ok']:<16} | "
            f"{stats['needs_check_ok']:<16} | {stats['passed']:<16} | {stats['median_latency_ms']} ms"
        )

    print("=" * 85)
    print(f"Report saved to: eval/reports/latest_eval.md")


if __name__ == "__main__":
    main()
