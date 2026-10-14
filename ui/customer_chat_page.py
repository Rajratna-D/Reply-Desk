"""Customer chat simulator designed like a modern messenger (WhatsApp/Instagram style)."""

import streamlit as st
from engine.db import connect, get_reply_by_id, get_seller_by_slug
from engine.service import draft_reply


def render_customer_chat_page(active_slug: str):
    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
    finally:
        conn.close()

    shop_name = seller["shop_name"] if seller else "Shop"
    shop_desc = seller["description"] if seller else "Local seller"

    # Split-screen demo hint banner
    st.markdown(
        """
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 8px 14px; font-size: 0.84rem; color: #6ee7b7; display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
            <span>📱 <strong>Simulated Customer Messenger</strong> — Place this window on the right half of your screen for the split-screen demo.</span>
            <span style="font-size: 0.76rem; color: #94a3b8;">Local SQLite • Zero external APIs</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_chat, col_info = st.columns([7, 4], gap="medium")

    # Session state for message tracking
    if "customer_reply_ids" not in st.session_state:
        st.session_state["customer_reply_ids"] = []

    # ----------------- LEFT COLUMN: The Messenger Viewport -----------------
    with col_chat:
        # Simulated Mobile Messenger Header
        st.markdown(
            f"""
            <div class="chat-device-header" style="border-radius: 12px 12px 0 0;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #059669 0%, #10b981 100%); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.05rem; color: #ffffff; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);">
                        {shop_name[0]}
                    </div>
                    <div>
                        <div style="font-weight: 600; font-size: 0.96rem; color: #f8fafc; display: flex; align-items: center; gap: 6px;">
                            {shop_name} <span style="color: #38bdf8; font-size: 0.85rem;" title="Verified Business">✓</span>
                        </div>
                        <div style="font-size: 0.74rem; color: #94a3b8; display: flex; align-items: center; gap: 6px;">
                            <span class="pulse-dot"></span> Active now on WhatsApp
                        </div>
                    </div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; background: rgba(255, 255, 255, 0.06); padding: 4px 10px; border-radius: 12px; color: #94a3b8;">
                        Buyer View
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Native scrolling container for chat messages
        with st.container(height=380, border=True):
            conn = connect()
            try:
                message_ids = st.session_state["customer_reply_ids"]
                if not message_ids:
                    # Welcome State
                    st.markdown(
                        f"""
                        <div style="text-align: center; padding: 45px 20px; color: #64748b;">
                            <div style="font-size: 2.4rem; margin-bottom: 8px;">🛍️</div>
                            <div style="font-size: 1.05rem; font-weight: 600; color: #e2e8f0; margin-bottom: 4px;">Direct WhatsApp Inquiry with {shop_name}</div>
                            <div style="font-size: 0.82rem; max-width: 360px; margin: 0 auto; line-height: 1.4;">
                                Ask about pricing, stock availability, sizes, delivery time, or custom orders in English, Hindi, Marathi, or Hinglish.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    for mid in message_ids:
                        row = get_reply_by_id(conn, mid)
                        if not row:
                            continue

                        # Customer message bubble (Right aligned, WhatsApp green)
                        time_str = row["created_at"].split(" ")[-1][:5] if " " in row["created_at"] else ""
                        st.markdown(
                            f"""
                            <div class="chat-bubble-customer">
                                <div>{row["customer_message"]}</div>
                                <div style="font-size: 0.68rem; opacity: 0.75; text-align: right; margin-top: 3px;">
                                    {time_str} <span style="color: #6ee7b7;">✓✓</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Shop reply status bubble (Left aligned)
                        action = row["seller_action"]
                        if action in ("sent_as_is", "edited"):
                            reply_body = row["final_reply"] if row["final_reply"] else row["drafted_reply"]
                            st.markdown(
                                f"""
                                <div class="chat-bubble-shop">
                                    <div style="font-size: 0.72rem; color: #34d399; font-weight: 600; margin-bottom: 3px;">{shop_name}</div>
                                    <div>{reply_body}</div>
                                    <div style="font-size: 0.68rem; opacity: 0.55; text-align: right; margin-top: 3px;">Delivered</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        elif action == "discarded":
                            pass
                        else:
                            # Pending owner approval in inbox
                            st.markdown(
                                """
                                <div class="chat-bubble-pending">
                                    <span class="pulse-dot" style="background-color: #f59e0b;"></span>
                                    <span>The shop owner is reviewing the drafted reply in their inbox...</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
            finally:
                conn.close()

        # Chat Input bar
        suggested_val = st.session_state.pop("suggested_prompt", "")
        col_input, col_send, col_ref = st.columns([5.5, 1.4, 1.1])

        with col_input:
            user_msg = st.text_input(
                "Message",
                value=suggested_val,
                placeholder="Type your message in English, Hindi, Marathi, or Hinglish...",
                label_visibility="collapsed",
                key="customer_chat_input",
            )

        with col_send:
            send_pressed = st.button("Send ➤", type="primary", use_container_width=True)

        with col_ref:
            if st.button("🔄", help="Refresh chat for new owner replies", use_container_width=True):
                st.rerun()

        if send_pressed and user_msg.strip():
            with st.spinner("Delivering message to shop inbox..."):
                try:
                    draft = draft_reply(
                        seller_slug=active_slug,
                        message=user_msg.strip(),
                        seller_action=None,  # Pending owner review
                    )
                    if draft.reply_id:
                        st.session_state["customer_reply_ids"].append(draft.reply_id)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ----------------- RIGHT COLUMN: Simulator Controls & Quick Prompts -----------------
    with col_info:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="font-weight: 700; font-size: 0.95rem; color: #f8fafc; margin-bottom: 4px;">
                    🏪 {shop_name}
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 12px; line-height: 1.4;">
                    {shop_desc}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div style="font-size: 0.74rem; font-weight: 600; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                    Test Personas & Prompts
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("🏷️ Normal Price Inquiry", use_container_width=True, help="Asks price of a catalogue item"):
                st.session_state["suggested_prompt"] = "Hi, what is the price and is it currently in stock?"
                st.rerun()

            if st.button("🚚 Shipping & Delivery Question", use_container_width=True, help="Tests delivery policy grounding"):
                st.session_state["suggested_prompt"] = "How many days does delivery take and what are the charges?"
                st.rerun()

            if st.button("⚠️ Out-of-Catalogue Inquiry", use_container_width=True, help="Triggers needs-check guardrail banner"):
                st.session_state["suggested_prompt"] = "Can you make a customized 3-tier gold plated cake with gluten-free almond base?"
                st.rerun()

            if st.button("🌐 Hindi / Hinglish Message", use_container_width=True, help="Tests language detection and tone matching"):
                st.session_state["suggested_prompt"] = "Bhaiya ye product Mumbai deliver ho sakta hai kya aur kitna time lagega?"
                st.rerun()

            st.divider()

            st.markdown(
                """
                <div style="font-size: 0.75rem; color: #94a3b8; line-height: 1.4;">
                    <strong>Demo Workflow:</strong><br/>
                    1. Send an inquiry here.<br/>
                    2. In the Owner window, click <strong>📥 Owner Inbox</strong>.<br/>
                    3. Approve or edit the draft.<br/>
                    4. See the reply delivered here!
                </div>
                """,
                unsafe_allow_html=True,
            )
