"""Customer chat simulator designed like a modern messenger (WhatsApp/Instagram style)."""

import html
import streamlit as st
from engine.db import connect, get_seller_by_slug, list_history
from engine.service import draft_reply


def send_customer_message(active_slug: str, message_text: str):
    """Deliver a customer message to SQLite and draft reply with local Gemma."""
    clean_msg = message_text.strip()
    if not clean_msg:
        return
    prior_queries = st.session_state.get("customer_prior_queries", [])
    with st.spinner("Delivering message to shop inbox..."):
        try:
            draft = draft_reply(
                seller_slug=active_slug,
                message=clean_msg,
                seller_action=None,  # Pending owner review
                prior_queries=prior_queries,
            )
            if "customer_prior_queries" not in st.session_state:
                st.session_state["customer_prior_queries"] = []
            st.session_state["customer_prior_queries"].append(clean_msg)
            if draft.reply_id:
                if "customer_reply_ids" not in st.session_state:
                    st.session_state["customer_reply_ids"] = []
                st.session_state["customer_reply_ids"].append(draft.reply_id)
            st.rerun()
        except Exception as e:
            st.error(f"Error drafting reply: {e}")


def render_customer_chat_page(active_slug: str):
    if st.session_state.get("customer_chat_active_slug") != active_slug:
        st.session_state["customer_chat_active_slug"] = active_slug
        st.session_state["customer_reply_ids"] = []
        st.session_state["customer_prior_queries"] = []

    if "customer_reply_ids" not in st.session_state:
        st.session_state["customer_reply_ids"] = []
    if "customer_prior_queries" not in st.session_state:
        st.session_state["customer_prior_queries"] = []

    session_ids = st.session_state["customer_reply_ids"]

    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if not seller:
            st.error(f"Shop '{active_slug}' not found.")
            return

        seller_id = seller["id"]
        chat_messages = []
        if session_ids:
            # Fetch only messages sent from this browser session
            placeholders = ",".join("?" for _ in session_ids)
            query = f"""
                SELECT id, seller_id, customer_message, drafted_reply, final_reply,
                       seller_action, created_at
                FROM reply_log
                WHERE seller_id = ? AND id IN ({placeholders})
                ORDER BY id ASC
            """
            rows = conn.execute(query, [seller_id] + session_ids).fetchall()
            chat_messages = [dict(r) for r in rows]
    finally:
        conn.close()

    shop_name = seller["shop_name"]
    shop_desc = seller["description"] or "Local seller"
    escaped_shop_name = html.escape(shop_name)
    escaped_shop_desc = html.escape(shop_desc)

    # Split-screen demo hint banner
    st.markdown(
        """
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 8px 14px; font-size: 0.84rem; color: #6ee7b7; display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
            <span>📱 <strong>Simulated Customer Messenger</strong> - Place this window on the right half of your screen for the split-screen demo.</span>
            <span style="font-size: 0.76rem; color: #94a3b8;">Local SQLite • Zero external APIs</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_chat, col_info = st.columns([7, 4], gap="medium")

    # ----------------- LEFT COLUMN: The Messenger Viewport -----------------
    with col_chat:
        # Simulated Mobile Messenger Header
        c_head_left, c_head_right = st.columns([4, 1.2])
        with c_head_left:
            st.markdown(
                f"""
                <div class="chat-device-header" style="border-radius: 12px 12px 0 0; padding: 10px 14px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #059669 0%, #10b981 100%); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.05rem; color: #ffffff; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);">
                            {escaped_shop_name[0] if escaped_shop_name else 'S'}
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 0.95rem; color: #f8fafc; display: flex; align-items: center; gap: 6px;">
                                {escaped_shop_name} <span style="color: #38bdf8; font-size: 0.85rem;" title="Verified Business">✓</span>
                            </div>
                            <div style="font-size: 0.74rem; color: #94a3b8; display: flex; align-items: center; gap: 6px;">
                                <span class="pulse-dot"></span> Active now on WhatsApp
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_head_right:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Refresh", help="Check for replies sent by the shop owner", use_container_width=True):
                st.rerun()

        # Native scrolling container for chat messages
        with st.container(height=400, border=True):
            if not chat_messages:
                # Welcome State
                st.markdown(
                    f"""
                    <div style="text-align: center; padding: 45px 20px; color: #64748b;">
                        <div style="font-size: 2.2rem; margin-bottom: 8px;">🛍️</div>
                        <div style="font-size: 1.05rem; font-weight: 600; color: #e2e8f0; margin-bottom: 4px;">Direct WhatsApp Inquiry with {escaped_shop_name}</div>
                        <div style="font-size: 0.82rem; max-width: 360px; margin: 0 auto; line-height: 1.4;">
                            Ask about pricing, stock availability, sizes, delivery time, or custom orders in English, Hindi, Marathi, or Hinglish.
                        </div>
                        <div style="font-size: 0.76rem; color: #94a3b8; margin-top: 14px;">
                            💡 Click any prompt button on the right to send an inquiry instantly!
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                for row in chat_messages:
                    # Customer message bubble (Right aligned, WhatsApp green)
                    time_str = row["created_at"].split(" ")[-1][:5] if " " in row["created_at"] else ""
                    escaped_user_msg = html.escape(row["customer_message"])
                    st.markdown(
                        f"""
                        <div class="chat-bubble-customer">
                            <div>{escaped_user_msg}</div>
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
                        raw_reply = row["final_reply"] if row["final_reply"] else row["drafted_reply"]
                        escaped_reply = html.escape(raw_reply)
                        st.markdown(
                            f"""
                            <div class="chat-bubble-shop">
                                <div style="font-size: 0.72rem; color: #34d399; font-weight: 600; margin-bottom: 3px;">{escaped_shop_name}</div>
                                <div>{escaped_reply}</div>
                                <div style="font-size: 0.68rem; opacity: 0.55; text-align: right; margin-top: 3px;">Delivered</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    elif action == "discarded":
                        st.markdown(
                            """
                            <div style="font-size: 0.76rem; color: #64748b; font-style: italic; margin-left: 10px; margin-bottom: 8px;">
                                ✕ The shop closed this inquiry without sending a response.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
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

        # Chat Input Form (supports Enter to send, and clears on submit)
        with st.form("customer_chat_form", clear_on_submit=True):
            col_in, col_btn = st.columns([5.8, 1.4])
            with col_in:
                user_msg = st.text_input(
                    "Message",
                    placeholder="Type a question and press Enter or Send...",
                    label_visibility="collapsed",
                )
            with col_btn:
                send_pressed = st.form_submit_button("Send ➤", type="primary", use_container_width=True)

            if send_pressed and user_msg.strip():
                send_customer_message(active_slug, user_msg.strip())

    # ----------------- RIGHT COLUMN: Simulator Controls & Quick Prompts -----------------
    with col_info:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="font-weight: 700; font-size: 0.95rem; color: #f8fafc; margin-bottom: 4px;">
                    🏪 {escaped_shop_name}
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 12px; line-height: 1.4;">
                    {escaped_shop_desc}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div style="font-size: 0.74rem; font-weight: 600; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                    Test Personas & Prompts (Instant Send)
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("🏷️ Normal Price Inquiry", use_container_width=True, help="Sends a catalogue price inquiry"):
                send_customer_message(active_slug, "Hi, what is the price of the oxidised jhumka and is it currently in stock?")

            if st.button("🚚 Shipping & Delivery Question", use_container_width=True, help="Sends a shipping policy inquiry"):
                send_customer_message(active_slug, "How many days does standard delivery take and what are the shipping charges?")

            if st.button("⚠️ Out-of-Catalogue Inquiry", use_container_width=True, help="Sends an out-of-scope question to test needs_check"):
                send_customer_message(active_slug, "Can you make a customized 3-tier gold plated cake with gluten-free almond base?")

            if st.button("🌐 Hindi / Hinglish Message", use_container_width=True, help="Sends a message in Hinglish"):
                send_customer_message(active_slug, "Bhaiya ye product Mumbai deliver ho sakta hai kya aur kitna time lagega?")

            if st.button("🗑️ Reset Chat View", use_container_width=True, help="Clears message history for this browser session"):
                st.session_state["customer_reply_ids"] = []
                st.session_state["customer_prior_queries"] = []
                st.rerun()

            st.divider()

            st.markdown(
                """
                <div style="font-size: 0.75rem; color: #94a3b8; line-height: 1.45;">
                    <strong>Demo Workflow:</strong><br/>
                    1. Click any test button above to send an inquiry.<br/>
                    2. In the Owner window, open <strong>📥 Owner Inbox</strong>.<br/>
                    3. Review safety flags, edit or approve the draft.<br/>
                    4. Click <strong>🔄 Refresh</strong> here to see the response delivered!
                </div>
                """,
                unsafe_allow_html=True,
            )
