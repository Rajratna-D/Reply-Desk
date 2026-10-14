"""History page for reviewing past drafts and actions."""

import json
import streamlit as st
from engine.db import connect, get_seller_by_slug, list_history


def render_history_page(active_slug: str):
    st.title("📜 Drafting History")
    st.caption("Audit past customer inquiries, generated drafts, and owner review actions.")

    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if not seller:
            st.warning(f"Shop '{active_slug}' not found.")
            return

        seller_id = seller["id"]

        # Filter bar
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
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
                "Filter by Needs Check:",
                options=["all", "flagged", "clean"],
                format_func=lambda x: {
                    "all": "All Drafts",
                    "flagged": "⚠️ Flagged (Needs Check)",
                    "clean": "🟢 Clean (No Flags)",
                }[x],
            )

        with col_f3:
            if st.button("🔄 Refresh History", use_container_width=True):
                st.rerun()

        history_rows = list_history(conn, seller_id, action_filter=action_choice)

        # Apply in-memory flag filter
        filtered_rows = []
        for r in history_rows:
            is_flagged = bool(r["needs_check"])
            if flag_choice == "flagged" and not is_flagged:
                continue
            if flag_choice == "clean" and is_flagged:
                continue
            filtered_rows.append(r)

        st.write(f"Showing **{len(filtered_rows)}** records:")

        if not filtered_rows:
            st.info("No history matching the selected criteria.")
            return

        for row in filtered_rows:
            action = row["seller_action"] or "pending"
            badge_class = {
                "sent_as_is": "badge-green",
                "edited": "badge-blue",
                "discarded": "badge-red",
                "pending": "badge-orange",
            }.get(action, "badge-orange")

            action_label = {
                "sent_as_is": "SENT AS IS",
                "edited": "SENT EDITED",
                "discarded": "DISCARDED",
                "pending": "PENDING",
            }.get(action, action.upper())

            with st.container(border=True):
                c_top1, c_top2 = st.columns([3, 2])
                with c_top1:
                    st.markdown(
                        f"""
                        <span class="badge {badge_class}">{action_label}</span>
                        <span style="font-size: 0.8rem; margin-left: 8px;">Lang: <code>{row['detected_language'] or 'unknown'}</code></span>
                        """,
                        unsafe_allow_html=True,
                    )
                with c_top2:
                    st.caption(f"{row['created_at']} • {row['latency_ms'] or 0} ms • `{row['model']}`")

                st.markdown(f"**Customer Message:** *\"{row['customer_message']}\"*")

                if row["final_reply"] and row["final_reply"] != row["drafted_reply"]:
                    st.markdown(f"**Final Sent Reply:** {row['final_reply']}")
                    with st.expander("Show original drafted reply"):
                        st.write(row["drafted_reply"])
                else:
                    st.markdown(f"**Drafted Reply:** {row['drafted_reply']}")

                if row["needs_check"]:
                    st.caption(f"⚠️ Flagged Reason: {row['check_reason'] or 'Unstated details'}")

    finally:
        conn.close()
