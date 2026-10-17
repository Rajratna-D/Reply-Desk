"""Owner inbox triage queue designed like a modern merchant support dashboard."""

import html
import json
import streamlit as st
from engine.db import connect, get_seller_by_slug, list_pending_replies, set_reply_action


def render_inbox_page(active_slug: str):
    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if not seller:
            st.warning(f"Shop '{active_slug}' not found.")
            return

        seller_id = seller["id"]
        pending_items = list_pending_replies(conn, seller_id)

        # Header with Metrics
        c_title, c_ref = st.columns([4, 1.2])
        with c_title:
            st.title("📥 Owner Inbox")
            st.caption(f"Triage & approval queue for **{seller['shop_name']}** • 100% on-device AI")
        with c_ref:
            if st.button("🔄 Refresh Queue", use_container_width=True):
                st.rerun()

        flagged_count = sum(1 for it in pending_items if it["needs_check"])
        clean_count = len(pending_items) - flagged_count

        # Metric Tiles
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f"""
                <div class="stat-tile">
                    <div class="stat-value">{len(pending_items)}</div>
                    <div class="stat-label">Pending Messages</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"""
                <div class="stat-tile">
                    <div class="stat-value" style="color: #34d399;">{clean_count}</div>
                    <div class="stat-label">Grounded Drafts</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"""
                <div class="stat-tile">
                    <div class="stat-value" style="color: #f87171;">{flagged_count}</div>
                    <div class="stat-label">Needs Check</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                """
                <div class="stat-tile">
                    <div class="stat-value" style="color: #818cf8;">100%</div>
                    <div class="stat-label">Private & Local</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if not pending_items:
            with st.container(border=True):
                st.markdown(
                    """
                    <div style="text-align: center; padding: 40px 20px;">
                        <div style="font-size: 2.4rem; margin-bottom: 10px;">✨</div>
                        <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">Inbox Zero</div>
                        <div style="color: #94a3b8; font-size: 0.88rem; max-width: 440px; margin: 0 auto; line-height: 1.5;">
                            All customer inquiries have been addressed. Open <strong>💬 Customer Chat</strong> in another window to test a simulated live buyer conversation!
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            return

        # Render each pending message inside its own clean container
        for item in pending_items:
            item_id = item["id"]
            cust_msg = item["customer_message"]
            draft_text = item["drafted_reply"]
            needs_check = bool(item["needs_check"])
            reason = item["check_reason"] or ""
            model_used = item["model"]
            latency = item["latency_ms"]
            lang = (item["detected_language"] or "en").upper()

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

            # Triage badge computation (Auto-Draft Ready, Policy Check, Needs Human)
            cust_msg_lower = cust_msg.lower()
            is_blocked = "prompt injection" in reason.lower() or "blocked" in reason.lower()
            is_unverified = bool(ungrounded) or "ungrounded" in reason.lower()

            if is_blocked or is_unverified or "private" in reason.lower():
                triage_badge = '<span class="rd-badge badge-flagged" style="font-weight: 700;">🚨 NEEDS HUMAN</span>'
            elif model_used == "gemma2:9b" or any(w in cust_msg_lower for w in ("refund", "return", "cancel", "damaged", "broken", "complaint", "wrong", "missing", "dispute")):
                triage_badge = '<span class="rd-badge badge-warning" style="font-weight: 700;">⚖️ POLICY CHECK</span>'
            else:
                triage_badge = '<span class="rd-badge badge-clean" style="font-weight: 700;">⚡ AUTO-DRAFT READY</span>'

            escaped_lang = html.escape(lang)
            escaped_model = html.escape(str(model_used))
            escaped_created = html.escape(str(item['created_at']))

            with st.container(border=True):
                # Header row: Tags & Telemetry
                c_meta_left, c_meta_right = st.columns([3, 2])
                with c_meta_left:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            {triage_badge}
                            <span class="rd-badge badge-lang">{escaped_lang}</span>
                            <span class="rd-badge badge-model">{escaped_model}</span>
                            <span style="font-size: 0.78rem; color: #64748b;">{escaped_created}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c_meta_right:
                    lat_sec = round((latency or 0) / 1000, 2)
                    st.markdown(
                        f"""
                        <div style="text-align: right; font-size: 0.8rem; color: #94a3b8;">
                            ⚡ Generated in <strong>{lat_sec}s</strong>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Customer Inquiry Box
                escaped_cust_msg = html.escape(cust_msg)
                escaped_reason = html.escape(reason or "The inquiry mentions details not in your shop catalogue.")
                st.markdown(
                    f"""
                    <div style="margin: 12px 0 14px 0; background: rgba(59, 130, 246, 0.05); border-left: 3px solid #3b82f6; border-radius: 0 8px 8px 0; padding: 12px 16px;">
                        <div style="font-size: 0.72rem; color: #93c5fd; text-transform: uppercase; font-weight: 600; letter-spacing: 0.04em; margin-bottom: 4px;">WhatsApp Customer Inquiry</div>
                        <div style="font-size: 1.05rem; color: #f8fafc; font-weight: 500;">"{escaped_cust_msg}"</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Guardrail Safety Banners
                if needs_check:
                    st.markdown(
                        f"""
                        <div class="alert-card-danger">
                            <strong>⚠️ Needs Owner Review:</strong> {escaped_reason}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        """
                        <div class="alert-card-success">
                            <strong>✓ Grounded Facts:</strong> All prices, variants, and policies verified against your shop data.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if ungrounded:
                    un_str = ", ".join(f"₹{a}" for a in ungrounded)
                    st.markdown(
                        f"""
                        <div class="alert-card-warning">
                            <strong>⚠️ Price Grounding Check:</strong> Mentions unverified amount(s): {un_str}.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if risk_list:
                    topics_str = ", ".join(t.replace("_", " ").title() for t in risk_list)
                    st.markdown(
                        f"""
                        <div class="alert-card-warning">
                            <strong>⚠️ Sensitive Topic:</strong> Detected topic(s): {topics_str}. Review carefully before approving.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Editable Draft Reply
                st.markdown(
                    """
                    <div style="font-size: 0.76rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 10px; margin-bottom: 5px;">
                        AI Draft - Edit if needed before approving:
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                edited_text = st.text_area(
                    "Drafted Reply",
                    value=draft_text,
                    key=f"inbox_reply_{item_id}",
                    label_visibility="collapsed",
                    height=95,
                )

                # Action Buttons
                col_b1, col_b2, col_b3, _ = st.columns([1.6, 1.8, 1.3, 2.5])
                with col_b1:
                    if st.button("✓ Send As Is", key=f"btn_send_{item_id}", type="primary", use_container_width=True):
                        set_reply_action(conn, item_id, "sent_as_is", final_reply=draft_text)
                        st.rerun()

                with col_b2:
                    if st.button("✏️ Send Edited", key=f"btn_edit_{item_id}", use_container_width=True):
                        clean_edited = edited_text.strip()
                        if not clean_edited:
                            st.error("Cannot send an empty reply. Please enter a message or discard.")
                        else:
                            set_reply_action(conn, item_id, "edited", final_reply=clean_edited)
                            st.rerun()

                with col_b3:
                    if st.button("✕ Discard", key=f"btn_discard_{item_id}", use_container_width=True):
                        set_reply_action(conn, item_id, "discarded")
                        st.rerun()

                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    finally:
        conn.close()
