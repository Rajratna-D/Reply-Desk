"""Owner inbox triage page for managing incoming simulated customer inquiries."""

import json
import streamlit as st
from engine.db import connect, get_seller_by_slug, list_pending_replies, set_reply_action


def render_inbox_page(active_slug: str):
    st.title("📥 Owner Inbox")
    st.caption("Review, edit, and send drafted replies to incoming customer inquiries.")

    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if not seller:
            st.warning(f"Shop '{active_slug}' not found.")
            return

        seller_id = seller["id"]
        pending_items = list_pending_replies(conn, seller_id)

        col_header, col_refresh = st.columns([4, 1])
        with col_header:
            st.subheader(f"Pending Messages ({len(pending_items)})")
        with col_refresh:
            if st.button("🔄 Refresh Inbox", use_container_width=True):
                st.rerun()

        if not pending_items:
            st.success("🎉 Inbox Zero! No pending messages awaiting review.")
            st.info("Tip: Open the **Customer Chat** in another browser window and send a message to see it appear here live.")
            return

        for item in pending_items:
            item_id = item["id"]
            cust_msg = item["customer_message"]
            draft_text = item["drafted_reply"]
            needs_check = bool(item["needs_check"])
            reason = item["check_reason"] or ""
            model_used = item["model"]
            latency = item["latency_ms"]

            ungrounded = []
            if item["ungrounded_amounts"]:
                try:
                    ungrounded = json.loads(item["ungrounded_amounts"])
                except Exception:
                    pass

            risk_list = []
            if item["risk_topics"]:
                try:
                    risk_list = json.loads(item["risk_topics"])
                except Exception:
                    pass

            with st.container(border=True):
                # Header row
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.markdown(f"**Customer Inquiry:** `{item['detected_language'] or 'unknown'}`")
                    st.markdown(f"> *\"{cust_msg}\"*")
                with c2:
                    st.caption(f"Received: {item['created_at']}")
                    if latency:
                        st.caption(f"⚡ {latency} ms via `{model_used}`")

                # Warning Banners
                if needs_check:
                    st.markdown(
                        f"""
                        <div class="alert-danger-box">
                            <strong>⚠️ Needs Owner Check:</strong> {reason or 'Question touched unstated or unverified details.'}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if ungrounded:
                    un_str = ", ".join(f"₹{a}" for a in ungrounded)
                    st.markdown(
                        f"""
                        <div class="alert-warning-box">
                            <strong>⚠️ Ungrounded Price Warning:</strong> Contains amount(s) not found in your shop data: {un_str}.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if risk_list:
                    topics_str = ", ".join(t.replace("_", " ").title() for t in risk_list)
                    st.markdown(
                        f"""
                        <div class="alert-warning-box">
                            <strong>⚠️ Double-check before sending:</strong> Mentions risk topic(s): {topics_str}.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Editable Draft
                edited_reply = st.text_area(
                    "Drafted Reply (edit before sending):",
                    value=draft_text,
                    key=f"inbox_reply_{item_id}",
                    height=100,
                )

                # Action buttons
                b_col1, b_col2, b_col3, _ = st.columns([1.5, 1.5, 1.2, 2.5])
                with b_col1:
                    if st.button("✅ Send as is", key=f"btn_send_{item_id}", use_container_width=True):
                        set_reply_action(conn, item_id, "sent_as_is", final_reply=draft_text)
                        st.success("Sent as is!")
                        st.rerun()

                with b_col2:
                    if st.button("✏️ Send edited", key=f"btn_edit_{item_id}", use_container_width=True):
                        set_reply_action(conn, item_id, "edited", final_reply=edited_reply.strip())
                        st.success("Sent edited reply!")
                        st.rerun()

                with b_col3:
                    if st.button("🗑️ Discard", key=f"btn_discard_{item_id}", use_container_width=True):
                        set_reply_action(conn, item_id, "discarded")
                        st.info("Draft discarded.")
                        st.rerun()

    finally:
        conn.close()
