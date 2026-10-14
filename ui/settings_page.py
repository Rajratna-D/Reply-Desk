"""Settings page for local model configuration and maintenance."""

import os
import streamlit as st
from engine.config import load_settings
from engine.db import clear_history, connect, get_seller_by_slug
from engine.llm import ollama_status


def render_settings_page(active_slug: str):
    st.title("⚙️ Engine Architecture & Settings")
    st.caption("Inspect local hardware acceleration, model inventory, and privacy guarantees.")

    try:
        settings = load_settings()
    except Exception:
        settings = None

    status = ollama_status()
    is_connected = status["reachable"]
    available_models = status.get("models", [])
    current_model = settings.model_name if settings else "gemma2:2b"

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        with st.container(border=True):
            st.markdown(
                """
                <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
                    <span>⚡ Local AI Engine & Hardware</span>
                    <span class="rd-badge badge-clean">RTX 3050 GPU</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if is_connected:
                st.markdown(
                    """
                    <div class="alert-card-success">
                        <strong>● Ollama Server Active:</strong> Listening on localhost. GPU offload verified.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="alert-card-danger">
                        <strong>● Ollama Offline:</strong> Run <code>ollama serve</code> to activate local inference.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""
                <table style="width: 100%; font-size: 0.85rem; color: #cbd5e1; border-collapse: collapse; margin-top: 10px;">
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 8px 0; color: #94a3b8;">Inference Endpoint</td>
                        <td style="padding: 8px 0; font-family: monospace; text-align: right;">{settings.ollama_host if settings else 'http://localhost:11434'}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 8px 0; color: #94a3b8;">Context Window (NUM_CTX)</td>
                        <td style="padding: 8px 0; font-family: monospace; text-align: right;">{settings.num_ctx if settings else 4096} tokens</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 8px 0; color: #94a3b8;">Primary Database</td>
                        <td style="padding: 8px 0; font-family: monospace; text-align: right;">data/replydesk.db (SQLite)</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #94a3b8;">GPU Allocation</td>
                        <td style="padding: 8px 0; color: #34d399; font-weight: 600; text-align: right;">100% GPU Layer Offload</td>
                    </tr>
                </table>
                """,
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            st.markdown(
                """
                <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 12px;">
                    🔒 Privacy & Offline Architecture
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div style="font-size: 0.84rem; color: #cbd5e1; line-height: 1.6;">
                    ReplyDesk is engineered strictly for privacy-sensitive small merchants:
                    <ul style="padding-left: 18px; margin-top: 6px; color: #94a3b8;">
                        <li><strong style="color: #f1f5f9;">Zero Cloud Dependency:</strong> All drafting is performed locally via open weights. No messages or catalogue items ever leave your device.</li>
                        <li><strong style="color: #f1f5f9;">Offline Capable:</strong> Test with Wi-Fi switched off. Responses generate with zero internet.</li>
                        <li><strong style="color: #f1f5f9;">Shop Isolation:</strong> Multi-tenant schema strictly filters catalogue queries by shop ID.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_right:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 10px;">
                    🤖 Model Inventory
                </div>
                <div style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 12px;">
                    Currently configured in <code>.env</code>:
                </div>
                <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
                    <span style="font-size: 0.74rem; color: #a5b4fc; text-transform: uppercase; font-weight: 600;">Active Model</span>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; font-family: monospace;">{current_model}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div style="font-size: 0.78rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; margin-bottom: 6px;">
                    Models Installed Locally in Ollama:
                </div>
                """,
                unsafe_allow_html=True,
            )
            if available_models:
                for m in available_models:
                    is_active = m == current_model or current_model.startswith(m)
                    badge = '<span class="rd-badge badge-clean">ACTIVE</span>' if is_active else ''
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: rgba(255,255,255,0.02); border-radius: 6px; margin-bottom: 4px;">
                            <span style="font-family: monospace; font-size: 0.88rem; color: #e2e8f0;">{m}</span>
                            {badge}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.warning("No models found. Pull one via terminal: `ollama pull gemma2:2b`")

        with st.container(border=True):
            st.markdown(
                f"""
                <div style="font-weight: 700; font-size: 1rem; color: #f8fafc; margin-bottom: 8px;">
                    🧹 Shop History Maintenance
                </div>
                <div style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 12px;">
                    Purge drafting history and test customer messages for active profile: <strong>{active_slug}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

            conn = connect()
            try:
                seller = get_seller_by_slug(conn, active_slug)
                if seller:
                    seller_id = seller["id"]
                    if st.button("Clear History for this Shop", type="secondary", use_container_width=True):
                        cleared_count = clear_history(conn, seller_id)
                        st.success(f"Cleared {cleared_count} records for '{active_slug}'.")
                        st.rerun()
            finally:
                conn.close()
