"""Manual reply drafting workbench."""

import html
import streamlit as st
from engine.db import connect, get_seller_by_slug, list_policies, list_products_full, save_faq_pair, set_reply_action
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
                height=120,
                label_visibility="collapsed",
                key="scratchpad_input_text",
            )

            # Reply Tone Selector
            tone_options = ["Warm Boutique", "Concise WhatsApp", "Polite Hinglish"]
            selected_tone = st.selectbox(
                "Reply Tone Style",
                tone_options,
                index=0,
                key="reply_tone_select",
                help="Switch tone style dynamically across boutique warmth, concise messaging, or polite Hinglish.",
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
                            draft = draft_reply(
                                active_slug,
                                customer_msg.strip(),
                                log=True,
                                tone_override=selected_tone,
                            )
                            st.session_state["manual_draft"] = draft
                        except Exception as err:
                            st.error(f"Generation error: {err}")

        # Grounded Knowledge Context Accordion
        escaped_shop_name = html.escape(seller["shop_name"])
        with st.expander(f"📚 {escaped_shop_name} Grounded Context ({len(products)} products, {len(policies)} policies)"):
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
                # Top Metadata Row
                c_m1, c_m2 = st.columns([3, 2])
                with c_m1:
                    if draft.needs_check:
                        st.markdown('<span class="rd-badge badge-flagged">⚠️ NEEDS CHECK</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="rd-badge badge-clean">✓ GROUNDED</span>', unsafe_allow_html=True)
                    st.markdown(f'<span class="rd-badge badge-lang">{html.escape(draft.language.upper())}</span>', unsafe_allow_html=True)
                with c_m2:
                    lat_sec = round(draft.latency_ms / 1000, 2)
                    st.markdown(
                        f'<div style="text-align: right; font-size: 0.78rem; color: #94a3b8;">⚡ {lat_sec}s • {html.escape(draft.model)}</div>',
                        unsafe_allow_html=True,
                    )

                # Transparent Telemetry Bar
                route_desc = draft.route_reason or "Fast Route"
                route_label = f"{draft.model} - {route_desc}"
                if draft.fallback_used:
                    route_label += f" (fallback from {draft.routed_model})"

                retrieval_label = "Hybrid RRF" if draft.retrieval_mode == "hybrid_rrf" else "SQLite FTS5"

                if draft.unverified_numbers:
                    grounding_label = f"Unverified Numbers Flagged ({', '.join(draft.unverified_numbers)})"
                    grounding_color = "#f87171"
                else:
                    grounding_label = "Verified"
                    grounding_color = "#34d399"

                st.markdown(
                    f"""
                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 8px 12px; margin: 10px 0; font-size: 0.78rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
                            <span style="color: #94a3b8;">Model & Route:</span>
                            <span style="color: #cbd5e1; font-family: monospace; font-weight: 600;">{html.escape(route_label)}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
                            <span style="color: #94a3b8;">Retrieval Mode:</span>
                            <span style="color: #818cf8; font-weight: 600;">{html.escape(retrieval_label)}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #94a3b8;">Numeric Grounding:</span>
                            <span style="color: {grounding_color}; font-weight: 600;">{html.escape(grounding_label)}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Warning callouts
                if draft.needs_check:
                    escaped_reason = html.escape(draft.reason)
                    st.markdown(
                        f"""
                        <div class="alert-card-danger" style="margin-top: 6px;">
                            <strong>⚠️ Notice:</strong> {escaped_reason}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if draft.ungrounded_amounts:
                    un_str = html.escape(", ".join(f"₹{a}" for a in draft.ungrounded_amounts))
                    st.markdown(
                        f"""
                        <div class="alert-card-warning">
                            <strong>⚠️ Ungrounded Price:</strong> {un_str} not in catalogue.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if draft.risk_topics:
                    topics_str = html.escape(", ".join(t.replace("_", " ").title() for t in draft.risk_topics))
                    st.markdown(
                        f"""
                        <div class="alert-card-warning">
                            <strong>⚠️ Sensitive Topic:</strong> {topics_str}.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Editable Text Area with dynamic key per draft
                edit_key = f"manual_edit_{draft.reply_id}" if draft.reply_id else f"manual_edit_{abs(hash(draft.reply))}"
                edited_draft = st.text_area(
                    "Final Reply",
                    value=draft.reply,
                    height=110,
                    key=edit_key,
                    label_visibility="collapsed",
                )

                # Quick Copy Box
                st.code(edited_draft, language="markdown")

                # 1-Click Save to Shop FAQ Checkbox
                save_to_faq = st.checkbox(
                    "💾 Save this Q&A to Shop FAQ upon approval",
                    value=False,
                    key=f"cb_save_faq_{draft.reply_id}",
                    help="Automatically adds this customer question and approved reply to shop policies so future queries match instantly.",
                )

                # Resolve Actions
                st.caption("Record action for history audit:")
                col_a1, col_a2, col_a3 = st.columns(3)

                conn = connect()
                try:
                    with col_a1:
                        if st.button("✓ Sent As Is", key=f"manual_btn_as_is_{draft.reply_id}", type="primary", use_container_width=True):
                            clean_text = draft.reply.strip()
                            if draft.reply_id:
                                set_reply_action(conn, draft.reply_id, "sent_as_is", final_reply=clean_text)
                            if save_to_faq and customer_msg.strip():
                                save_faq_pair(conn, seller["id"], customer_msg.strip(), clean_text, language=draft.language)
                                st.success("Saved Q&A pair to Shop FAQ!")
                            st.success("Logged as sent!")

                    with col_a2:
                        if st.button("✏️ Sent Edited", key=f"manual_btn_edited_{draft.reply_id}", use_container_width=True):
                            clean_edited = edited_draft.strip()
                            if not clean_edited:
                                st.error("Cannot send an empty reply.")
                            else:
                                if draft.reply_id:
                                    set_reply_action(conn, draft.reply_id, "edited", final_reply=clean_edited)
                                if save_to_faq and customer_msg.strip():
                                    save_faq_pair(conn, seller["id"], customer_msg.strip(), clean_edited, language=draft.language)
                                    st.success("Saved Q&A pair to Shop FAQ!")
                                st.success("Logged edited draft!")

                    with col_a3:
                        if st.button("✕ Discard", key=f"manual_btn_discard_{draft.reply_id}", use_container_width=True):
                            if draft.reply_id:
                                set_reply_action(conn, draft.reply_id, "discarded")
                            st.info("Logged as discarded.")
                finally:
                    conn.close()
