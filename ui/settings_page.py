"""Settings page for local model configuration and maintenance."""

import os
import streamlit as st
from engine.config import load_settings
from engine.db import clear_history, connect, get_seller_by_slug
from engine.llm import ollama_status


def render_settings_page(active_slug: str):
    st.title("⚙️ System Settings")
    st.caption("Inspect local hardware usage, swap open-weight models, and manage logs.")

    try:
        settings = load_settings()
    except Exception:
        settings = None

    status = ollama_status()
    is_connected = status["reachable"]
    available_models = status.get("models", [])

    st.subheader("🤖 Local AI Engine (Ollama)")

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Ollama Host:** `{settings.ollama_host if settings else 'http://localhost:11434'}`")
        if is_connected:
            st.success("🟢 Ollama Server is Connected and Healthy")
        else:
            st.error("🔴 Ollama Server is Unreachable. Please run 'ollama serve'.")

    with c2:
        st.write(f"**Context Window (`NUM_CTX`):** `{settings.num_ctx if settings else 4096}` tokens")
        st.write(f"**Database:** `{settings.db_path if settings else 'data/replydesk.db'}`")

    st.divider()

    st.subheader("Model Selection")
    st.write(
        "ReplyDesk never hardcodes model names. The active model is determined by "
        "your environment (`MODEL_NAME`)."
    )

    current_model = settings.model_name if settings else "gemma2:2b"
    st.info(f"**Currently Active Model:** `{current_model}`")

    if available_models:
        st.write("**Models Installed in Local Ollama:**")
        for m in available_models:
            st.markdown(f"- `{m}`")
    else:
        st.warning("No models found in Ollama. Pull one with: `ollama pull gemma2:2b`")

    st.divider()

    st.subheader("🧹 Shop Data Maintenance")
    st.write(f"Manage history for active shop: **{active_slug}**")

    conn = connect()
    try:
        seller = get_seller_by_slug(conn, active_slug)
        if seller:
            seller_id = seller["id"]
            if st.button("Clear Drafting History for this Shop", type="secondary"):
                cleared_count = clear_history(conn, seller_id)
                st.success(f"Cleared {cleared_count} history records for '{active_slug}'.")
                st.rerun()
    finally:
        conn.close()
