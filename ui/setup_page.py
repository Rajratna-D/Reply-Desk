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
    st.title("🏪 Shop Setup & Catalogue")
    st.caption("Configure shop details, products, policies, tone, and import/export shop profiles.")

    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if not seller:
            st.error(f"Shop '{active_slug}' not found.")
            return

        seller_id = seller["id"]

        tab_shop, tab_prod, tab_pol, tab_samp, tab_io = st.tabs([
            "Shop Profile",
            "Products & Catalogue",
            "Policies",
            "Style Samples",
            "Import / Export",
        ])

        # ----------------- TAB 1: Shop Profile -----------------
        with tab_shop:
            st.subheader("Shop Identity & Tone")
            cur = conn.cursor()
            cur.execute("SELECT language FROM seller_languages WHERE seller_id = ?;", (seller_id,))
            current_langs = [r["language"] for r in cur.fetchall()]

            with st.form("shop_details_form"):
                name = st.text_input("Shop Name", value=seller["shop_name"])
                desc = st.text_area("About the Shop", value=seller["description"] or "")
                tone = st.text_input(
                    "Tone & Persona",
                    value=seller["tone"],
                    help="e.g. 'Warm and short. Uses ji in Hindi. At most 1 emoji.'",
                )
                def_lang = st.selectbox(
                    "Default Language",
                    options=LANGUAGES,
                    index=LANGUAGES.index(seller["default_language"]) if seller["default_language"] in LANGUAGES else 0,
                )
                sel_langs = st.multiselect(
                    "Supported Reply Languages",
                    options=LANGUAGES,
                    default=current_langs or [seller["default_language"]],
                )

                if st.form_submit_button("Save Shop Details"):
                    if not sel_langs:
                        st.error("Select at least one supported language.")
                    elif def_lang not in sel_langs:
                        st.error(f"Default language '{def_lang}' must be selected in Supported Languages.")
                    else:
                        save_shop_details(conn, seller_id, name, desc, tone, def_lang, sel_langs)
                        st.success("Shop details saved!")
                        st.rerun()

        # ----------------- TAB 2: Products & Catalogue -----------------
        with tab_prod:
            st.subheader("Product Catalogue")
            products = list_products_full(conn, seller_id)

            col_p1, col_p2 = st.columns([3, 2])
            with col_p1:
                st.write(f"**Total items:** {len(products)}")
                for p in products:
                    with st.expander(f"📦 [{p['sku']}] {p['name']} ({p['stock_status']})"):
                        st.write(f"**Category:** {p['category'] or 'None'}")
                        if p["description"]:
                            st.write(f"**Description:** {p['description']}")
                        if p["notes"]:
                            st.write(f"**Notes:** {p['notes']}")
                        st.write("**Variants & Prices:**")
                        for v in p["variants"]:
                            st.write(f"- {v['label']}: **₹{v['price_inr']}**")

                        if st.button("Delete Product", key=f"del_prod_{p['id']}", type="secondary"):
                            delete_product(conn, p["id"])
                            st.success(f"Deleted {p['sku']}")
                            st.rerun()

            with col_p2:
                st.write("**Add / Update Product**")
                with st.form("add_product_form"):
                    p_sku = st.text_input("SKU", placeholder="e.g. UT-105")
                    p_name = st.text_input("Product Name", placeholder="e.g. Linen Kurti")
                    p_cat = st.text_input("Category", placeholder="e.g. Kurti")
                    p_desc = st.text_input("Short Description", placeholder="e.g. Breathable summer linen")
                    p_stock = st.selectbox("Stock Status", options=STOCK_STATUSES)
                    p_notes = st.text_input("Notes (Allergens, restock, custom info)")

                    st.caption("Default Variant & Price:")
                    var_label = st.text_input("Variant Label", value="Standard")
                    var_price = st.number_input("Price (₹ INR)", min_value=0, value=999, step=10)

                    if st.form_submit_button("Add Product"):
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

                st.divider()
                st.write("**Bulk Import via CSV**")
                csv_file = st.file_uploader("Upload products.csv", type=["csv"])
                if csv_file and st.button("Import CSV"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(csv_file.getvalue())
                        tmp_path = tmp.name
                    try:
                        count = import_products_csv(conn, active_slug, tmp_path)
                        st.success(f"Successfully imported {count} products from CSV!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"CSV import failed: {err}")

        # ----------------- TAB 3: Policies -----------------
        with tab_pol:
            st.subheader("Shop Policies")
            policies = list_policies(conn, seller_id)

            p_col1, p_col2 = st.columns([3, 2])
            with p_col1:
                st.write(f"**Current Policies ({len(policies)}):**")
                for pol in policies:
                    with st.expander(f"📋 {pol['topic'].upper()} — {pol['title']}"):
                        st.write(pol["body"])
                        if st.button("Delete Policy", key=f"del_pol_{pol['id']}"):
                            delete_policy(conn, pol["id"])
                            st.success("Policy removed.")
                            st.rerun()

            with p_col2:
                st.write("**Add Policy**")
                with st.form("add_policy_form"):
                    pol_topic = st.selectbox("Policy Topic", options=POLICY_TOPICS)
                    pol_title = st.text_input("Title", placeholder="e.g. Return Window")
                    pol_body = st.text_area(
                        "Policy Body",
                        placeholder="State exact facts, numbers, days, or rupee charges clearly.",
                    )
                    if st.form_submit_button("Save Policy"):
                        if not pol_title.strip() or not pol_body.strip():
                            st.error("Title and Body are required.")
                        else:
                            add_policy(conn, seller_id, pol_topic, pol_title.strip(), pol_body.strip())
                            st.success("Policy saved!")
                            st.rerun()

        # ----------------- TAB 4: Sample Replies (Style) -----------------
        with tab_samp:
            st.subheader("Sample Replies (Few-Shot Style Examples)")
            st.caption("Provide 2 to 6 examples showing how this shop speaks to customers.")
            samples = list_sample_replies(conn, seller_id)

            s_col1, s_col2 = st.columns([3, 2])
            with s_col1:
                for s in samples:
                    with st.expander(f"💬 [{s['language'].upper()}] {s['customer_message'][:40]}..."):
                        st.write(f"**Customer:** {s['customer_message']}")
                        st.write(f"**Reply:** {s['reply']}")
                        if st.button("Delete Sample", key=f"del_samp_{s['id']}"):
                            delete_sample_reply(conn, s["id"])
                            st.success("Sample removed.")
                            st.rerun()

            with s_col2:
                st.write("**Add Style Example**")
                with st.form("add_sample_form"):
                    s_lang = st.selectbox("Language", options=LANGUAGES)
                    s_msg = st.text_input("Customer Inquiry", placeholder="e.g. What sizes do you have?")
                    s_rep = st.text_area("Ideal Reply", placeholder="Write the reply exactly in the seller's tone.")
                    if st.form_submit_button("Add Sample"):
                        if not s_msg.strip() or not s_rep.strip():
                            st.error("Both message and reply are required.")
                        else:
                            add_sample_reply(conn, seller_id, s_lang, s_msg.strip(), s_rep.strip())
                            st.success("Sample reply added!")
                            st.rerun()

        # ----------------- TAB 5: Import / Export -----------------
        with tab_io:
            st.subheader("Backup & Profile Transfer")
            # Export
            try:
                exported_data = export_config(conn, active_slug)
                json_str = json.dumps(exported_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 Download Shop Configuration (JSON)",
                    data=json_str,
                    file_name=f"{active_slug}.json",
                    mime="application/json",
                )
            except Exception as e:
                st.error(f"Export error: {e}")

            st.divider()
            st.subheader("Import a New or Updated Shop")
            import_file = st.file_uploader("Upload seller.json config", type=["json"])
            replace_existing = st.checkbox("Overwrite existing shop if slug matches", value=True)

            if import_file and st.button("Import Configuration"):
                try:
                    data = json.load(import_file)
                    new_id = import_config(conn, data, replace=replace_existing)
                    new_slug = data["shop"]["slug"]
                    st.success(f"Successfully imported shop '{new_slug}' (ID {new_id})!")
                    st.session_state["active_slug"] = new_slug
                    st.rerun()
                except ConfigError as err:
                    st.error(f"Config Validation Error: {err}")
                except Exception as err:
                    st.error(f"Import Error: {err}")

    finally:
        conn.close()
