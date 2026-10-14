"""History page for reviewing past drafts and actions."""

import html
import json
import streamlit as st
from engine.db import connect, get_seller_by_slug, list_history


def render_history_page(active_slug: str):
    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if not seller:
            st.warning(f"Shop '{active_slug}' not found.")
            return

        seller_id = seller["id"]

        st.title("📜 Drafting History & Audit")
        st.caption(f"Review past customer inquiries, generated drafts, and merchant actions for **{seller['shop_name']}**")

        all_records = list_history(conn, seller_id, action_filter="all")

        # Top Metric Tiles
        total_count = len(all_records)
        as_is_count = sum(1 for r in all_records if r["seller_action"] == "sent_as_is")
        edited_count = sum(1 for r in all_records if r["seller_action"] == "edited")
        flagged_count = sum(1 for r in all_records if r["needs_check"])

        accept_rate = round(((as_is_count + edited_count) / total_count * 100), 1) if total_count > 0 else 0.0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f"""
                <div class="stat-tile">
                    <div class="stat-value">{total_count}</div>
                    <div class="stat-label">Total Drafts</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"""
                <div class="stat-tile">
                    <div class="stat-value" style="color: #34d399;">{as_is_count}</div>
                    <div class="stat-label">Sent As Is</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"""
                <div class="stat-tile">
                    <div class="stat-value" style="color: #818cf8;">{edited_count}</div>
                    <div class="stat-label">Sent Edited</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f"""
                <div class="stat-tile">
                    <div class="stat-value" style="color: #38bdf8;">{accept_rate}%</div>
                    <div class="stat-label">Merchant Approval</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # Filter bar
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1.2])
        with col_f1:
            action_choice = st.selectbox(
                "Filter by Action:",
                options=["all", "pending", "sent_as_is", "edited", "discarded"],
                format_func=lambda x: {
                    "all": "All Actions",
                    "pending": "⏳ Pending Review",
                    "sent_as_is": "✅ Sent As Is",
                    "edited": "✏️ Sent Edited",
                    "discarded": "🗑️ Discarded",
                }[x],
            )

        with col_f2:
            flag_choice = st.selectbox(
                "Filter by Grounding:",
                options=["all", "clean", "flagged"],
                format_func=lambda x: {
                    "all": "All Drafts",
                    "clean": "🟢 Clean (Grounded)",
                    "flagged": "⚠️ Flagged (Needs Check)",
                }[x],
            )

        with col_f3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        history_rows = list_history(conn, seller_id, action_filter=action_choice, limit=100)

        # Apply in-memory flag filter
        filtered_rows = []
        for r in history_rows:
            is_flagged = bool(r["needs_check"])
            if flag_choice == "flagged" and not is_flagged:
                continue
            if flag_choice == "clean" and is_flagged:
                continue
            filtered_rows.append(r)

        if not filtered_rows:
            with st.container(border=True):
                st.markdown(
                    """
                    <div style="text-align: center; padding: 35px 20px; color: #64748b;">
                        <div style="font-size: 2rem; margin-bottom: 6px;">📜</div>
                        <div style="font-size: 1rem; font-weight: 600; color: #94a3b8;">No matching history records</div>
                        <div style="font-size: 0.8rem; margin-top: 4px;">Adjust your filters or generate new drafts.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            return

        for row in filtered_rows:
            action = row["seller_action"] or "pending"

            badge_html = {
                "sent_as_is": '<span class="rd-badge badge-clean">✓ SENT AS IS</span>',
                "edited": '<span class="rd-badge badge-model">✏️ SENT EDITED</span>',
                "discarded": '<span class="rd-badge badge-flagged">✕ DISCARDED</span>',
                "pending": '<span class="rd-badge badge-warning">⏳ PENDING REVIEW</span>',
            }.get(action, '<span class="rd-badge badge-warning">PENDING</span>')

            lang = (row["detected_language"] or "en").upper()
            lat_sec = round((row["latency_ms"] or 0) / 1000, 2)

            with st.container(border=True):
                c_top1, c_top2 = st.columns([3, 2])
                with c_top1:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 8px;">
                            {badge_html}
                            <span class="rd-badge badge-lang">{lang}</span>
                            <span style="font-size: 0.76rem; color: #64748b;">{row['created_at']}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c_top2:
                    st.markdown(
                        f"""
                        <div style="text-align: right; font-size: 0.78rem; color: #94a3b8;">
                            ⚡ {lat_sec}s • <code>{row['model']}</code>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                escaped_cust_msg = html.escape(row["customer_message"])
                st.markdown(
                    f"""
                    <div style="margin: 10px 0; background: rgba(255, 255, 255, 0.02); border-left: 2px solid #3b82f6; border-radius: 0 6px 6px 0; padding: 8px 12px;">
                        <span style="font-size: 0.72rem; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Customer Question:</span>
                        <div style="font-size: 0.95rem; color: #f8fafc; margin-top: 2px;">"{escaped_cust_msg}"</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if row["final_reply"] and row["final_reply"] != row["drafted_reply"]:
                    escaped_final = html.escape(row["final_reply"])
                    st.markdown(
                        f"""
                        <div style="margin-bottom: 6px;">
                            <span style="font-size: 0.72rem; color: #34d399; font-weight: 600; text-transform: uppercase;">Final Sent Reply (Edited):</span>
                            <div style="font-size: 0.92rem; color: #f1f5f9; background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 6px; padding: 8px 12px; margin-top: 2px;">
                                {escaped_final}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.expander("View initial AI draft"):
                        st.caption(row["drafted_reply"])
                else:
                    escaped_draft = html.escape(row["drafted_reply"])
                    st.markdown(
                        f"""
                        <div style="margin-bottom: 6px;">
                            <span style="font-size: 0.72rem; color: #818cf8; font-weight: 600; text-transform: uppercase;">Drafted Reply:</span>
                            <div style="font-size: 0.92rem; color: #f1f5f9; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; padding: 8px 12px; margin-top: 2px;">
                                {escaped_draft}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if row["needs_check"]:
                    escaped_flag = html.escape(row["check_reason"] or "Uncatalogued details")
                    st.markdown(
                        f"""
                        <div style="font-size: 0.78rem; color: #f87171; background: rgba(239, 68, 68, 0.08); border-radius: 4px; padding: 4px 8px; margin-top: 6px;">
                            ⚠️ <strong>Flagged:</strong> {escaped_flag}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    finally:
        conn.close()
