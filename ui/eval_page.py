"""Model benchmarks and evaluation results dashboard for ReplyDesk."""

import html
import json
from pathlib import Path
import streamlit as st

from engine.config import load_settings
from engine.db import connect, get_eval_results, get_eval_run, list_eval_runs
from eval.run_eval import run_evaluation

REPORTS_DIR = Path(__file__).resolve().parent.parent / "eval" / "reports"


def render_eval_page(active_slug: str):
    conn = connect()
    try:
        settings = load_settings()
        active_model = settings.model_name
    except Exception:
        active_model = "gemma2:2b"

    st.title("📊 Model Benchmarks & Quality Evaluation")
    st.caption(
        "Measure and verify factual grounding, script adherence, and latency on standardized "
        "customer test cases across English, Hindi, Marathi, and Hinglish."
    )

    tab_overview, tab_runner, tab_reports = st.tabs([
        "📈 Benchmark Results",
        "▶️ Run Live Evaluation",
        "📑 Markdown Reports",
    ])

    # ------------------ TAB 1: Benchmark Results ------------------
    with tab_overview:
        runs = list_eval_runs(conn, limit=30)
        if not runs:
            st.info("No benchmark evaluation runs recorded yet. Switch to 'Run Live Evaluation' to execute your first benchmark.")
        else:
            run_options = {
                r["id"]: f"Run #{r['id']} - {r['model']} ({r['started_at']}) - {r['passed_total']}/{r['total_cases']} passed"
                for r in runs
            }
            selected_run_id = st.selectbox(
                "Select Evaluation Run:",
                options=list(run_options.keys()),
                format_func=lambda x: run_options[x],
                help="Switch between evaluation runs to compare model quality across versions and configurations.",
            )

            current_run = get_eval_run(conn, selected_run_id)
            results = get_eval_results(conn, selected_run_id)

            if results:
                total_cases = len(results)
                facts_passed = sum(1 for r in results if r["facts_ok"])
                check_passed = sum(1 for r in results if r["needs_check_ok"])
                lang_passed = sum(1 for r in results if r["language_ok"])
                overall_passed = sum(1 for r in results if r["facts_ok"] and r["needs_check_ok"] and r["language_ok"])

                latencies = [r["latency_ms"] for r in results if r["latency_ms"] and r["latency_ms"] > 0]
                avg_latency = round(sum(latencies) / len(latencies), 0) if latencies else 0

                pass_rate = round(overall_passed / total_cases * 100, 1) if total_cases > 0 else 0.0
                facts_rate = round(facts_passed / total_cases * 100, 1) if total_cases > 0 else 0.0
                check_rate = round(check_passed / total_cases * 100, 1) if total_cases > 0 else 0.0
                lang_rate = round(lang_passed / total_cases * 100, 1) if total_cases > 0 else 0.0

                # Metric Cards
                m1, m2, m3, m4, m5 = st.columns(5)
                with m1:
                    pass_color = "#34d399" if pass_rate >= 80 else ("#f59e0b" if pass_rate >= 60 else "#f87171")
                    st.markdown(
                        f"""
                        <div class="stat-tile">
                            <div class="stat-value" style="color: {pass_color};">{overall_passed}/{total_cases}</div>
                            <div class="stat-label">Overall Pass ({pass_rate}%)</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with m2:
                    st.markdown(
                        f"""
                        <div class="stat-tile">
                            <div class="stat-value" style="color: #60a5fa;">{facts_rate}%</div>
                            <div class="stat-label">Facts Grounded ({facts_passed}/{total_cases})</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with m3:
                    st.markdown(
                        f"""
                        <div class="stat-tile">
                            <div class="stat-value" style="color: #a78bfa;">{check_rate}%</div>
                            <div class="stat-label">Needs-Check Flags</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with m4:
                    st.markdown(
                        f"""
                        <div class="stat-tile">
                            <div class="stat-value" style="color: #38bdf8;">{lang_rate}%</div>
                            <div class="stat-label">Script Adherence</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with m5:
                    st.markdown(
                        f"""
                        <div class="stat-tile">
                            <div class="stat-value" style="color: #cbd5e1;">{int(avg_latency)} ms</div>
                            <div class="stat-label">Avg Reply Latency</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

                # Slice Breakdown Table
                st.markdown(
                    """
                    <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 8px;">
                        Performance Breakdown by Language & Split
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                slices = {
                    "All Cases": results,
                    "English (en)": [r for r in results if r["language"] == "en"],
                    "Hindi (hi)": [r for r in results if r["language"] == "hi"],
                    "Marathi (mr)": [r for r in results if r["language"] == "mr"],
                    "Hinglish": [r for r in results if r["language"] == "hinglish"],
                    "dev Split": [r for r in results if r["split"] == "dev"],
                    "test Split": [r for r in results if r["split"] == "test"],
                }

                table_rows = []
                for s_name, s_rows in slices.items():
                    c_count = len(s_rows)
                    if c_count == 0:
                        continue
                    f_ok = sum(1 for r in s_rows if r["facts_ok"])
                    chk_ok = sum(1 for r in s_rows if r["needs_check_ok"])
                    l_ok = sum(1 for r in s_rows if r["language_ok"])
                    tot_ok = sum(1 for r in s_rows if r["facts_ok"] and r["needs_check_ok"] and r["language_ok"])
                    s_lats = [r["latency_ms"] for r in s_rows if r["latency_ms"] and r["latency_ms"] > 0]
                    med_lat = int(sorted(s_lats)[len(s_lats) // 2]) if s_lats else 0
                    rate = round(tot_ok / c_count * 100, 1)

                    table_rows.append(
                        f"<tr>"
                        f"<td style='font-weight: 600; color: #f1f5f9;'>{s_name}</td>"
                        f"<td style='text-align: center; color: #cbd5e1;'>{c_count}</td>"
                        f"<td style='text-align: center; color: #60a5fa;'>{f_ok}/{c_count}</td>"
                        f"<td style='text-align: center; color: #a78bfa;'>{chk_ok}/{c_count}</td>"
                        f"<td style='text-align: center; color: #38bdf8;'>{l_ok}/{c_count}</td>"
                        f"<td style='text-align: center; font-weight: 700; color: {'#34d399' if rate >= 80 else '#f59e0b'};'>{tot_ok}/{c_count} ({rate}%)</td>"
                        f"<td style='text-align: center; color: #94a3b8;'>{med_lat} ms</td>"
                        f"</tr>"
                    )

                html_table = f"""
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; overflow: hidden; margin-bottom: 20px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.86rem;">
                        <thead>
                            <tr style="background: rgba(30, 41, 59, 0.8); border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                                <th style="text-align: left; padding: 10px 14px; color: #94a3b8; font-weight: 600;">Slice</th>
                                <th style="text-align: center; padding: 10px 8px; color: #94a3b8; font-weight: 600;">Cases</th>
                                <th style="text-align: center; padding: 10px 8px; color: #94a3b8; font-weight: 600;">Facts Grounded</th>
                                <th style="text-align: center; padding: 10px 8px; color: #94a3b8; font-weight: 600;">Needs-Check OK</th>
                                <th style="text-align: center; padding: 10px 8px; color: #94a3b8; font-weight: 600;">Script OK</th>
                                <th style="text-align: center; padding: 10px 8px; color: #94a3b8; font-weight: 600;">Overall Pass</th>
                                <th style="text-align: center; padding: 10px 14px; color: #94a3b8; font-weight: 600;">Median Latency</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(table_rows)}
                        </tbody>
                    </table>
                </div>
                """
                st.markdown(html_table, unsafe_allow_html=True)

                # Filterable Case Inspector
                st.markdown(
                    """
                    <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 8px;">
                        Case-by-Case Inspection
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col_flt1, col_flt2 = st.columns([2, 2])
                with col_flt1:
                    filter_status = st.selectbox("Filter Status:", ["All Cases", "Passed Only", "Failures Only"], key="eval_status_filter")
                with col_flt2:
                    filter_lang = st.selectbox("Filter Language:", ["All Languages", "en", "hi", "mr", "hinglish"], key="eval_lang_filter")

                for r in results:
                    is_passed = bool(r["facts_ok"] and r["needs_check_ok"] and r["language_ok"])
                    if filter_status == "Passed Only" and not is_passed:
                        continue
                    if filter_status == "Failures Only" and is_passed:
                        continue
                    if filter_lang != "All Languages" and r["language"] != filter_lang:
                        continue

                    badge_color = "#10b981" if is_passed else "#ef4444"
                    badge_label = "PASS" if is_passed else "FAIL"
                    exp_title = f"{'✅' if is_passed else '❌'} [{r['case_id']}] {r['shop_slug']} ({r['language'].upper()}) - {r['category']} - {r['latency_ms']} ms"

                    with st.expander(exp_title):
                        c_esc_reply = html.escape(r["reply"])
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.caption(f"Facts Grounding: {'✅ OK' if r['facts_ok'] else '❌ Missing / Hallucinated'}")
                        with c2:
                            st.caption(f"Needs Check: {'✅ OK' if r['needs_check_ok'] else '❌ Mismatch'}")
                        with c3:
                            st.caption(f"Script Match: {'✅ OK' if r['language_ok'] else '❌ Script Issue'}")
                        with c4:
                            st.caption(f"Tokens: {r['prompt_tokens'] or '-'} in / {r['output_tokens'] or '-'} out")

                        st.markdown(
                            f"""
                            <div style="margin-top: 8px;">
                                <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 600; text-transform: uppercase;">AI Drafted Reply:</div>
                                <div style="font-size: 0.92rem; color: #f1f5f9; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 10px 14px; margin-top: 4px;">
                                    {c_esc_reply}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    # ------------------ TAB 2: Run Live Evaluation ------------------
    with tab_runner:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 6px;">
                Execute Benchmark Evaluation
            </div>
            <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 16px;">
                Run the standardized 25-case evaluation suite against your local model. Results are stored in the SQLite database and exported as markdown.
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("eval_runner_form"):
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                run_model = st.text_input("Model Tag", value=active_model, help="Ollama model tag e.g. gemma2:2b")
            with c_r2:
                run_split = st.selectbox("Dataset Split", options=["all", "dev", "test"], format_func=lambda s: {
                    "all": "All Cases (25 questions)",
                    "dev": "Dev Split (12 questions - faster)",
                    "test": "Test Split (13 questions)",
                }[s])

            run_notes = st.text_input("Run Notes (Optional)", placeholder="e.g. RTX 3050 6GB local run, NUM_CTX=4096")
            submitted = st.form_submit_button("▶️ Launch Live Benchmark", type="primary", use_container_width=True)

        if submitted:
            progress_bar = st.progress(0, text="Initializing evaluation run...")
            status_text = st.empty()

            def live_progress(idx, total, case):
                pct = int((idx / total) * 100)
                progress_bar.progress(pct, text=f"Evaluating [{idx+1}/{total}] {case['id']} ({case['shop']} - {case['language']})...")

            try:
                summary = run_evaluation(
                    model=run_model.strip(),
                    split_filter=run_split,
                    notes=run_notes.strip() or None,
                    progress_callback=live_progress,
                )
                progress_bar.progress(100, text="Evaluation completed successfully!")
                st.success(
                    f"Benchmark finished! Overall Pass Rate: {summary['overall_pass_rate']}% "
                    f"({summary['total_cases']} cases evaluated). View results in the 'Benchmark Results' tab."
                )
                st.rerun()
            except Exception as e:
                st.error(f"Evaluation failed: {e}")

    # ------------------ TAB 3: Markdown Reports ------------------
    with tab_reports:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 6px;">
                Generated Markdown Reports
            </div>
            <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 14px;">
                Exported evaluation summaries formatted for the challenge submission post.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if REPORTS_DIR.exists():
            reports = sorted(list(REPORTS_DIR.glob("*.md")), key=lambda p: p.stat().st_mtime, reverse=True)
            if not reports:
                st.info("No report files found in eval/reports.")
            else:
                rep_names = [p.name for p in reports]
                chosen_rep_name = st.selectbox("Select Report:", rep_names)
                chosen_path = REPORTS_DIR / chosen_rep_name
                report_content = chosen_path.read_text(encoding="utf-8")

                st.download_button(
                    "📥 Download Markdown Report",
                    data=report_content,
                    file_name=chosen_rep_name,
                    mime="text/markdown",
                    type="primary",
                )
                with st.expander("Preview Markdown Content", expanded=True):
                    st.markdown(report_content)
        else:
            st.info("No reports directory found yet. Run an evaluation to generate one.")

    conn.close()
