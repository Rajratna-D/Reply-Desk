"""Simulated customer chat page for side-by-side demo."""

import streamlit as st
from engine.db import connect, get_reply_by_id, list_sellers
from engine.service import draft_reply


def render_customer_chat_page(active_slug: str):
    st.markdown(
        """
        <div class="demo-banner">
            <span>ℹ️</span>
            <strong>Simulated chat for demo.</strong> Not connected to WhatsApp or Instagram.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.title("💬 Customer Chat (Simulated)")
    st.caption("Ask questions about products, prices, stock, delivery, or policies in English, Hindi, Marathi, or Hinglish.")

    # Initialize browser session message tracking
    if "customer_reply_ids" not in st.session_state:
        st.session_state["customer_reply_ids"] = []

    conn = connect()
    try:
        # Load and display chat messages for this customer session
        message_ids = st.session_state["customer_reply_ids"]
        if message_ids:
            for mid in message_ids:
                row = get_reply_by_id(conn, mid)
                if not row:
                    continue

                # 1. Customer bubble
                st.markdown(
                    f"""
                    <div class="chat-bubble-customer">
                        <div>{row["customer_message"]}</div>
                        <div class="chat-meta">You • {row["created_at"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # 2. Shop response bubble
                action = row["seller_action"]
                if action in ("sent_as_is", "edited"):
                    reply_text = row["final_reply"] if row["final_reply"] else row["drafted_reply"]
                    st.markdown(
                        f"""
                        <div class="chat-bubble-shop">
                            <div>{reply_text}</div>
                            <div class="chat-meta">Shop Owner • Replied</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                elif action == "discarded":
                    # Discarded drafts show no answer to customer
                    pass
                else:
                    # Pending review by owner
                    st.markdown(
                        """
                        <div class="chat-bubble-shop" style="opacity: 0.85; font-style: italic;">
                            <div>⏳ The shop will reply shortly.</div>
                            <div class="chat-meta">Awaiting shop owner review</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No messages sent yet. Ask something below to test the simulated customer experience!")

    finally:
        conn.close()

    # Message input form
    with st.form("customer_input_form", clear_on_submit=True):
        customer_msg = st.text_input(
            "Type your message to the shop:",
            placeholder="e.g. How much is the cotton kurti? / केक ऑर्डर करायला किती दिवस लागतील?",
        )
        col1, col2 = st.columns([1, 5])
        with col1:
            submitted = st.form_submit_button("Send Message", use_container_width=True)
        with col2:
            refresh = st.form_submit_button("🔄 Refresh Status", use_container_width=False)

    if refresh:
        st.rerun()

    if submitted:
        cleaned_msg = customer_msg.strip()
        if not cleaned_msg:
            st.warning("Please enter a message before sending.")
            return

        with st.spinner("Sending message to shop..."):
            try:
                # Draft reply immediately and store as pending (seller_action=None)
                draft = draft_reply(
                    seller_slug=active_slug,
                    message=cleaned_msg,
                    seller_action=None,  # Pending owner review
                )
                if draft.reply_id:
                    st.session_state["customer_reply_ids"].append(draft.reply_id)
                st.rerun()
            except Exception as e:
                st.error(f"Error reaching shop assistant: {e}")
