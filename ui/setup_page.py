"""Shop setup, catalogue management, policy editor, and import/export page."""

import json
import tempfile
from pathlib import Path
import streamlit as st

from engine.db import (
    add_or_update_product,
    add_policy,
    add_sample_reply,
    connect,
    delete_policy,
    delete_product,
    delete_sample_reply,
    get_seller_by_slug,
    list_policies,
    list_products_full,
    list_sample_replies,
    save_shop_details,
    search_products_full,
)
from engine.importer import (
    ConfigError,
    export_config,
    import_config,
    import_products_csv,
)

LANGUAGES = ["en", "hi", "mr", "hinglish"]
STOCK_STATUSES = ["in_stock", "low_stock", "out_of_stock", "made_to_order"]
POLICY_TOPICS = ["delivery", "returns", "payment", "hours", "ordering", "other"]


def render_setup_page(active_slug: str):
    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if not seller:
            st.error(f"Shop '{active_slug}' not found.")
            return

        seller_id = seller["id"]

        st.title("🏪 Shop Setup & Knowledge Base")
        st.caption(f"Manage profile, catalogue, policies, and tone for **{seller['shop_name']}**")

        tab_shop, tab_prod, tab_pol, tab_samp, tab_io = st.tabs([
            "Shop Profile & Persona",
            "Catalogue & Products",
            "Policies & Grounding",
            "Style Examples",
            "Backup & Transfer",
        ])

        # ----------------- TAB 1: Shop Profile -----------------
        with tab_shop:
            cur = conn.cursor()
            cur.execute("SELECT language FROM seller_languages WHERE seller_id = ?;", (seller_id,))
            current_langs = [r["language"] for r in cur.fetchall()]

            col_form, col_guide = st.columns([7, 4], gap="large")

            with col_form:
                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 12px;">
                            Shop Identity & Tone
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.form("shop_details_form"):
                        name = st.text_input("Shop Name", value=seller["shop_name"])
                        desc = st.text_area("About the Shop (Bio)", value=seller["description"] or "", height=85)
                        tone = st.text_input(
                            "Tone & Persona Instructions",
                            value=seller["tone"],
                            help="e.g. 'Warm and short. Uses ji in Hindi. At most 1 emoji.'",
                        )
                        c_lang1, c_lang2 = st.columns(2)
                        with c_lang1:
                            def_lang = st.selectbox(
                                "Default Language",
                                options=LANGUAGES,
                                index=LANGUAGES.index(seller["default_language"]) if seller["default_language"] in LANGUAGES else 0,
                            )
                        with c_lang2:
                            sel_langs = st.multiselect(
                                "Supported Reply Languages",
                                options=LANGUAGES,
                                default=current_langs or [seller["default_language"]],
                            )

                        if st.form_submit_button("Save Shop Profile", type="primary"):
                            if not sel_langs:
                                st.error("Select at least one supported language.")
                            elif def_lang not in sel_langs:
                                st.error(f"Default language '{def_lang}' must be selected in Supported Languages.")
                            else:
                                save_shop_details(conn, seller_id, name, desc, tone, def_lang, sel_langs)
                                st.success("Shop profile updated successfully!")
                                st.rerun()

            with col_guide:
                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 600; font-size: 0.9rem; color: #cbd5e1; margin-bottom: 8px;">
                            💡 Persona Guidance
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8; line-height: 1.5;">
                            Small Indian social sellers thrive on warmth and personal connection:
                            <ul style="padding-left: 18px; margin-top: 6px;">
                                <li><strong>Warmth:</strong> Using "Ji" or polite greetings makes customers feel valued.</li>
                                <li><strong>Concision:</strong> WhatsApp customers prefer quick 2-3 line answers over walls of text.</li>
                                <li><strong>Restraint:</strong> ReplyDesk limits emojis to max 1-2 per reply.</li>
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # ----------------- TAB 2: Products & Catalogue -----------------
        with tab_prod:
            col_p1, col_p2 = st.columns([6, 5], gap="large")

            with col_p1:
                search_query = st.text_input(
                    "Search Catalogue (FTS5)",
                    placeholder="Search by keyword, material, or category...",
                    key=f"search_prod_{seller_id}",
                    label_visibility="collapsed",
                )

                if search_query.strip():
                    products = search_products_full(conn, seller_id, search_query.strip())
                else:
                    products = list_products_full(conn, seller_id)

                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <span style="font-weight: 700; font-size: 1rem; color: #f8fafc;">
                            {'Filtered Search Results' if search_query.strip() else 'Active Catalogue'}
                        </span>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <span class="rd-badge badge-lang" style="font-size: 0.72rem;">⚡ FTS5 Search</span>
                            <span class="rd-badge badge-clean">{len(products)} Items</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not products:
                    if search_query.strip():
                        st.info(f"No products found matching '{search_query.strip()}'.")
                    else:
                        st.info("No products registered. Add your first item using the form on the right.")

                for p in products:
                    status_color = {
                        "in_stock": "#10b981",
                        "low_stock": "#f59e0b",
                        "out_of_stock": "#ef4444",
                        "made_to_order": "#8b5cf6",
                    }.get(p["stock_status"], "#94a3b8")

                    with st.container(border=True):
                        c_card_top1, c_card_top2 = st.columns([3, 1])
                        with c_card_top1:
                            st.markdown(
                                f"""
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span class="rd-badge badge-lang" style="font-family: monospace;">{p['sku']}</span>
                                    <span style="font-weight: 700; font-size: 0.96rem; color: #f8fafc;">{p['name']}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with c_card_top2:
                            st.markdown(
                                f"""
                                <div style="text-align: right; font-size: 0.72rem; color: {status_color}; font-weight: 600; text-transform: uppercase;">
                                    ● {p['stock_status'].replace('_', ' ')}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        if p["description"]:
                            st.markdown(f"<div style='font-size: 0.82rem; color: #94a3b8; margin: 4px 0 8px 0;'>{p['description']}</div>", unsafe_allow_html=True)

                        # Variants and prices
                        v_pills = " ".join(
                            f"<span style='background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 6px; font-size: 0.76rem; color: #e2e8f0; margin-right: 6px;'>{v['label']}: <strong>₹{v['price_inr']}</strong></span>"
                            for v in p["variants"]
                        )
                        st.markdown(f"<div style='margin-bottom: 8px;'>{v_pills}</div>", unsafe_allow_html=True)

                        c_del, _ = st.columns([1.2, 3])
                        with c_del:
                            if st.button("Delete", key=f"del_prod_{p['id']}", type="secondary", use_container_width=True):
                                delete_product(conn, p["id"])
                                st.rerun()

            with col_p2:
                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 12px;">
                            Add or Update Item
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.form("add_product_form"):
                        c_sku, c_stock = st.columns(2)
                        with c_sku:
                            p_sku = st.text_input("SKU", placeholder="e.g. UT-105")
                        with c_stock:
                            p_stock = st.selectbox("Stock Status", options=STOCK_STATUSES)

                        p_name = st.text_input("Product Name", placeholder="e.g. Handblock Linen Kurti")
                        p_cat = st.text_input("Category", placeholder="e.g. Apparel / Kurti")
                        p_desc = st.text_input("Description", placeholder="e.g. Breathable pure linen summer wear")
                        p_notes = st.text_input("Special Notes (Allergens, custom sizing, care)")

                        st.markdown("<div style='font-size: 0.76rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; margin-top: 8px;'>Variant & Price</div>", unsafe_allow_html=True)
                        c_vl, c_vp = st.columns([2, 1.5])
                        with c_vl:
                            var_label = st.text_input("Variant Label", value="Standard")
                        with c_vp:
                            var_price = st.number_input("Price (₹ INR)", min_value=0, value=999, step=10)

                        if st.form_submit_button("Add to Catalogue", type="primary", use_container_width=True):
                            if not p_sku.strip() or not p_name.strip():
                                st.error("SKU and Name are required.")
                            else:
                                add_or_update_product(
                                    conn=conn,
                                    seller_id=seller_id,
                                    sku=p_sku.strip(),
                                    name=p_name.strip(),
                                    category=p_cat.strip(),
                                    description=p_desc.strip(),
                                    attributes={},
                                    stock_status=p_stock,
                                    notes=p_notes.strip(),
                                    variants=[{"label": var_label.strip(), "price_inr": int(var_price)}],
                                )
                                st.success(f"Saved product '{p_sku}'")
                                st.rerun()

                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 700; font-size: 0.95rem; color: #f8fafc; margin-bottom: 8px;">
                            📁 Bulk Import via CSV
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    csv_file = st.file_uploader("Upload products.csv", type=["csv"], label_visibility="collapsed")
                    if csv_file and st.button("Import CSV Items", use_container_width=True):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                            tmp.write(csv_file.getvalue())
                            tmp_path = tmp.name
                        try:
                            count = import_products_csv(conn, active_slug, tmp_path)
                            st.success(f"Successfully imported {count} products!")
                            st.rerun()
                        except Exception as err:
                            st.error(f"CSV import failed: {err}")

        # ----------------- TAB 3: Policies -----------------
        with tab_pol:
            policies = list_policies(conn, seller_id)
            p_col1, p_col2 = st.columns([6, 5], gap="large")

            with p_col1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <span style="font-weight: 700; font-size: 1rem; color: #f8fafc;">Active Grounding Policies</span>
                        <span class="rd-badge badge-clean">{len(policies)} Rules</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                topic_icons = {
                    "delivery": "🚚",
                    "returns": "🔄",
                    "payment": "💳",
                    "hours": "⏰",
                    "ordering": "📦",
                    "other": "📋",
                }

                for pol in policies:
                    icon = topic_icons.get(pol["topic"], "📋")
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                <span>{icon}</span>
                                <span class="rd-badge badge-lang">{pol['topic'].upper()}</span>
                                <span style="font-weight: 700; font-size: 0.92rem; color: #f8fafc;">{pol['title']}</span>
                            </div>
                            <div style="font-size: 0.84rem; color: #cbd5e1; line-height: 1.45; margin-bottom: 8px;">
                                {pol['body']}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        can_del_pol = len(policies) > 1
                        if st.button("Delete Policy", key=f"del_pol_{pol['id']}", type="secondary", disabled=not can_del_pol):
                            delete_policy(conn, pol["id"])
                            st.rerun()
                        if not can_del_pol:
                            st.caption("At least 1 policy is required for grounded answers.")

            with p_col2:
                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 12px;">
                            Add Shop Policy
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.form("add_policy_form"):
                        pol_topic = st.selectbox("Policy Category", options=POLICY_TOPICS)
                        pol_title = st.text_input("Title", placeholder="e.g. Metro Delivery Window")
                        pol_body = st.text_area(
                            "Exact Policy Terms",
                            placeholder="State exact days, shipping charges in INR, or return terms clearly.",
                            height=120,
                        )
                        if st.form_submit_button("Save Policy", type="primary", use_container_width=True):
                            if not pol_title.strip() or not pol_body.strip():
                                st.error("Title and Body are required.")
                            else:
                                add_policy(conn, seller_id, pol_topic, pol_title.strip(), pol_body.strip())
                                st.success("Policy saved!")
                                st.rerun()

        # ----------------- TAB 4: Sample Replies (Style) -----------------
        with tab_samp:
            samples = list_sample_replies(conn, seller_id)
            s_col1, s_col2 = st.columns([6, 5], gap="large")

            with s_col1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <span style="font-weight: 700; font-size: 1rem; color: #f8fafc;">Few-Shot Style Examples</span>
                        <span class="rd-badge badge-clean">{len(samples)} Examples</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                for s in samples:
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="margin-bottom: 6px;">
                                <span class="rd-badge badge-lang">{s['language'].upper()}</span>
                            </div>
                            <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px;">
                                <strong>Buyer:</strong> "{s['customer_message']}"
                            </div>
                            <div style="font-size: 0.88rem; color: #6ee7b7; font-weight: 500; margin-bottom: 8px;">
                                <strong>Seller:</strong> "{s['reply']}"
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        can_del_samp = len(samples) > 2
                        if st.button("Delete Example", key=f"del_samp_{s['id']}", type="secondary", disabled=not can_del_samp):
                            delete_sample_reply(conn, s["id"])
                            st.rerun()
                        if not can_del_samp:
                            st.caption("Minimum 2 style examples required for tone grounding.")

            with s_col2:
                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 12px;">
                            Add Few-Shot Style Example
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if len(samples) >= 6:
                        st.info("Maximum 6 style examples reached. Delete an existing example to add a new one.")
                    else:
                        with st.form("add_sample_form"):
                            s_lang = st.selectbox("Language", options=LANGUAGES)
                            s_msg = st.text_input("Customer Inquiry", placeholder="e.g. What sizes do you have?")
                            s_rep = st.text_area("Ideal Seller Reply", placeholder="Write the reply matching your tone.", height=90)
                            if st.form_submit_button("Add Example", type="primary", use_container_width=True):
                                if not s_msg.strip() or not s_rep.strip():
                                    st.error("Both message and reply are required.")
                                else:
                                    add_sample_reply(conn, seller_id, s_lang, s_msg.strip(), s_rep.strip())
                                    st.success("Sample added!")
                                    st.rerun()

        # ----------------- TAB 5: Import / Export -----------------
        with tab_io:
            col_exp, col_imp = st.columns(2, gap="large")

            with col_exp:
                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 8px;">
                            📥 Export Shop Configuration
                        </div>
                        <div style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 14px;">
                            Download the complete JSON definition of this shop including catalogue, policies, and style samples.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    try:
                        exported_data = export_config(conn, active_slug)
                        json_str = json.dumps(exported_data, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="Download Profile JSON",
                            data=json_str,
                            file_name=f"{active_slug}.json",
                            mime="application/json",
                            type="primary",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"Export error: {e}")

            with col_imp:
                with st.container(border=True):
                    st.markdown(
                        """
                        <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 8px;">
                            📤 Import Shop Configuration
                        </div>
                        <div style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 14px;">
                            Upload a <code>seller.json</code> configuration file to import a new shop profile.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    import_file = st.file_uploader("Upload seller.json", type=["json"], label_visibility="collapsed")
                    replace_existing = st.checkbox("Overwrite existing shop if slug matches", value=True)

                    if import_file and st.button("Import Configuration", type="primary", use_container_width=True):
                        try:
                            data = json.load(import_file)
                            new_id = import_config(conn, data, replace=replace_existing)
                            new_slug = data["shop"]["slug"]
                            st.success(f"Successfully imported shop '{new_slug}'!")
                            st.session_state["active_slug"] = new_slug
                            st.rerun()
                        except ConfigError as err:
                            st.error(f"Config Validation Error: {err}")
                        except Exception as err:
                            st.error(f"Import Error: {err}")

    finally:
        conn.close()
