"""Manual reply drafting workbench."""

import streamlit as st
from engine.db import connect, get_seller_by_slug, list_policies, list_products_full, set_reply_action
from engine.service import draft_reply


def render_reply_page(active_slug: str):
    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        products = list_products_full(conn, seller["id"]) if seller else []
        policies = list_policies(conn, seller["id"]) if seller else []
    finally:
        conn.close()

    st.title("✍️ Manual Reply Workbench")
    st.caption("Draft, verify, and fine-tune grounded replies for WhatsApp or Instagram messages.")

    if "manual_draft" not in st.session_state:
        st.session_state["manual_draft"] = None

    col_left, col_right = st.columns([1, 1], gap="large")

    # ----------------- LEFT COLUMN: Input & Knowledge Context -----------------
    with col_left:
        with st.container(border=True):
            st.markdown(
                """
                <div style="font-weight: 700; font-size: 0.95rem; color: #f8fafc; margin-bottom: 6px;">
                    Incoming Customer Message
                </div>
                """,
                unsafe_allow_html=True,
            )

            customer_msg = st.text_area(
                "Customer message input",
                placeholder="Paste customer WhatsApp / Instagram chat inquiry here...",
                height=140,
                label_visibility="collapsed",
                key="scratchpad_input_text",
            )

            btn_col, _ = st.columns([1.6, 2])
            with btn_col:
                generate_clicked = st.button("✨ Draft Reply", type="primary", use_container_width=True)

            if generate_clicked:
                if not customer_msg.strip():
                    st.warning("Please paste or type a customer message.")
                else:
                    with st.spinner("Analyzing catalogue & drafting reply with Gemma 2..."):
                        try:
                            draft = draft_reply(active_slug, customer_msg.strip(), log=True)
                            st.session_state["manual_draft"] = draft
                        except Exception as err:
                            st.error(f"Generation error: {err}")

        # Grounded Knowledge Context Accordion
        with st.expander(f"📚 {seller['shop_name']} Grounded Context ({len(products)} products, {len(policies)} policies)"):
            st.caption(f"**Tone:** {seller['tone']}")
            st.markdown("**Catalog Items:**")
            for p in products:
                prices_str = ", ".join(f"{v['label']} (₹{v['price_inr']})" for v in p["variants"])
                st.markdown(f"- **{p['name']}** [{p['sku']}]: {prices_str} • *{p['stock_status']}*")
            st.markdown("**Key Policies:**")
            for pol in policies[:5]:
                st.markdown(f"- **{pol['title']}:** {pol['body']}")

    # ----------------- RIGHT COLUMN: AI Draft & Safety Assessment -----------------
    with col_right:
        draft = st.session_state.get("manual_draft")
        with st.container(border=True):
            st.markdown(
                """
                <div style="font-weight: 700; font-size: 0.95rem; color: #f8fafc; margin-bottom: 8px;">
                    Grounded AI Draft & Safety Review
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not draft:
                st.markdown(
                    """
                    <div style="text-align: center; padding: 45px 20px; color: #64748b;">
                        <div style="font-size: 2.2rem; margin-bottom: 8px;">💬</div>
                        <div style="font-size: 0.95rem; font-weight: 600; color: #94a3b8;">Awaiting Customer Message</div>
                        <div style="font-size: 0.8rem; margin-top: 4px; line-height: 1.4;">
                            Paste an inquiry on the left and click <strong>Draft Reply</strong>.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                # Metadata Row
                c_m1, c_m2 = st.columns([3, 2])
                with c_m1:
                    if draft.needs_check:
                        st.markdown('<span class="rd-badge badge-flagged">⚠️ NEEDS CHECK</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="rd-badge badge-clean">✓ GROUNDED</span>', unsafe_allow_html=True)
                    st.markdown(f'<span class="rd-badge badge-lang">{draft.language.upper()}</span>', unsafe_allow_html=True)
                with c_m2:
                    lat_sec = round(draft.latency_ms / 1000, 2)
                    st.markdown(
                        f'<div style="text-align: right; font-size: 0.78rem; color: #94a3b8;">⚡ {lat_sec}s • {draft.model}</div>',
                        unsafe_allow_html=True,
                    )

                # Warning callouts
                if draft.needs_check:
                    st.markdown(
                        f"""
                        <div class="alert-card-danger" style="margin-top: 10px;">
                            <strong>⚠️ Notice:</strong> {draft.reason}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if draft.ungrounded_amounts:
                    un_str = ", ".join(f"₹{a}" for a in draft.ungrounded_amounts)
                    st.markdown(
                        f"""
                        <div class="alert-card-warning">
                            <strong>⚠️ Ungrounded Price:</strong> {un_str} not in catalogue.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if draft.risk_topics:
                    topics_str = ", ".join(t.replace("_", " ").title() for t in draft.risk_topics)
                    st.markdown(
                        f"""
                        <div class="alert-card-warning">
                            <strong>⚠️ Sensitive Topic:</strong> {topics_str}.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Editable Text Area
                edited_draft = st.text_area(
                    "Final Reply",
                    value=draft.reply,
                    height=110,
                    key="manual_edit_area",
                    label_visibility="collapsed",
                )

                # Quick Copy Box
                st.code(edited_draft, language="markdown")

                # Resolve Actions
                st.caption("Record action for history audit:")
                col_a1, col_a2, col_a3 = st.columns(3)

                conn = connect()
                try:
                    with col_a1:
                        if st.button("✓ Sent As Is", key="manual_btn_as_is", type="primary", use_container_width=True):
                            if draft.reply_id:
                                set_reply_action(conn, draft.reply_id, "sent_as_is", final_reply=draft.reply)
                            st.success("Logged as sent!")

                    with col_a2:
                        if st.button("✏️ Sent Edited", key="manual_btn_edited", use_container_width=True):
                            if draft.reply_id:
                                set_reply_action(conn, draft.reply_id, "edited", final_reply=edited_draft.strip())
                            st.success("Logged edited draft!")

                    with col_a3:
                        if st.button("✕ Discard", key="manual_btn_discard", use_container_width=True):
                            if draft.reply_id:
                                set_reply_action(conn, draft.reply_id, "discarded")
                            st.info("Logged as discarded.")
                finally:
                    conn.close()
