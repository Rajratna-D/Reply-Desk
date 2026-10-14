"""Manual reply drafting scratchpad page."""

import streamlit as st
from engine.db import connect, set_reply_action
from engine.service import draft_reply


def render_reply_page(active_slug: str):
    st.title("✍️ Draft a Reply")
    st.caption("Paste any customer inquiry to generate a verified, grounded reply.")

    # Session state for scratchpad draft
    if "manual_draft" not in st.session_state:
        st.session_state["manual_draft"] = None

    customer_msg = st.text_area(
        "Customer message:",
        placeholder="Paste customer WhatsApp / Instagram chat message here...",
        height=100,
    )

    col_btn, _ = st.columns([1.5, 4])
    with col_btn:
        generate_clicked = st.button("✨ Draft Reply", type="primary", use_container_width=True)

    if generate_clicked:
        if not customer_msg.strip():
            st.warning("Please enter a customer message first.")
            return

        with st.spinner("Drafting reply using local open-weight model..."):
            try:
                draft = draft_reply(active_slug, customer_msg.strip(), log=True)
                st.session_state["manual_draft"] = draft
            except Exception as e:
                st.error(f"Drafting failed: {e}")
                return

    # Render current draft if available
    draft = st.session_state.get("manual_draft")
    if draft:
        st.divider()
        st.subheader("Drafted Reply")

        # Warnings / Flags
        if draft.needs_check:
            st.markdown(
                f"""
                <div class="alert-danger-box">
                    <strong>⚠️ Needs Check:</strong> {draft.reason}
                </div>
                """,
                unsafe_allow_html=True,
            )

        if draft.ungrounded_amounts:
            un_str = ", ".join(f"₹{a}" for a in draft.ungrounded_amounts)
            st.markdown(
                f"""
                <div class="alert-warning-box">
                    <strong>⚠️ Ungrounded Price Warning:</strong> Contains price(s) not in shop data: {un_str}.
                </div>
                """,
                unsafe_allow_html=True,
            )

        if draft.risk_topics:
            topics_str = ", ".join(t.replace("_", " ").title() for t in draft.risk_topics)
            st.markdown(
                f"""
                <div class="alert-warning-box">
                    <strong>⚠️ Double-check before sending:</strong> Mentions risk topic: {topics_str}.
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Output editor
        edited_text = st.text_area(
            "Review & Edit Draft:",
            value=draft.reply,
            height=120,
            key="scratchpad_edited_reply",
        )

        # Meta indicators
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.caption(f"Language: `{draft.language}`")
        with col_m2:
            st.caption(f"Latency: `{draft.latency_ms} ms`")
        with col_m3:
            st.caption(f"Model: `{draft.model}`")

        # Feedback & Actions
        st.write("Mark action taken:")
        b1, b2, b3 = st.columns(3)

        conn = connect()
        try:
            with b1:
                if st.button("✅ Sent as is", use_container_width=True):
                    if draft.reply_id:
                        set_reply_action(conn, draft.reply_id, "sent_as_is", final_reply=draft.reply)
                    st.success("Logged as sent without changes.")

            with b2:
                if st.button("✏️ Sent edited", use_container_width=True):
                    if draft.reply_id:
                        set_reply_action(conn, draft.reply_id, "edited", final_reply=edited_text.strip())
                    st.success("Logged with your edits saved.")

            with b3:
                if st.button("🗑️ Discarded", use_container_width=True):
                    if draft.reply_id:
                        set_reply_action(conn, draft.reply_id, "discarded")
                    st.info("Logged as discarded.")
        finally:
            conn.close()
