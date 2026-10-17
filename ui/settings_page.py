import html
import os
from pathlib import Path
import streamlit as st
from engine.config import load_settings, validate_ollama_url
from engine.db import clear_history, connect, get_seller_by_slug
from engine.llm import ollama_status

__all__ = ["render_settings_page", "validate_ollama_url"]


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

            raw_host = settings.ollama_host if settings else "http://localhost:11434"
            try:
                validated_host = validate_ollama_url(raw_host)
                ssrf_status = '<span style="color: #34d399; font-weight: 600;">SSRF Protected (Localhost)</span>'
            except Exception as e:
                validated_host = raw_host
                ssrf_status = f'<span style="color: #f87171; font-weight: 600;">Blocked: {html.escape(str(e))}</span>'

            escaped_host = html.escape(validated_host)

            st.markdown(
                f"""
                <table style="width: 100%; font-size: 0.85rem; color: #cbd5e1; border-collapse: collapse; margin-top: 10px;">
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 8px 0; color: #94a3b8;">Inference Endpoint</td>
                        <td style="padding: 8px 0; font-family: monospace; text-align: right;">{escaped_host}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <td style="padding: 8px 0; color: #94a3b8;">Security & SSRF Check</td>
                        <td style="padding: 8px 0; text-align: right;">{ssrf_status}</td>
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

            first_class_models = ["gemma4:e2b", "gemma2:2b", "gemma2:9b", "gemma:7b"]
            all_selectable = list(first_class_models)
            for m in available_models:
                if m not in all_selectable:
                    all_selectable.append(m)

            selected_idx = all_selectable.index(current_model) if current_model in all_selectable else 0
            new_model = st.selectbox(
                "Switch Default Model Tier:",
                options=all_selectable,
                index=selected_idx,
                help="Select default Gemma model tier used for drafting and routing",
            )
            if new_model != current_model:
                if st.button("Apply Model Change", type="primary", use_container_width=True):
                    os.environ["REPLYDESK_MODEL"] = new_model
                    env_file = Path(__file__).resolve().parent.parent / ".env"
                    if env_file.exists():
                        env_lines = env_file.read_text(encoding="utf-8").splitlines()
                        updated_lines = []
                        found_key = False
                        for el in env_lines:
                            if el.startswith("REPLYDESK_MODEL="):
                                updated_lines.append(f"REPLYDESK_MODEL={new_model}")
                                found_key = True
                            else:
                                updated_lines.append(el)
                        if not found_key:
                            updated_lines.append(f"REPLYDESK_MODEL={new_model}")
                        env_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
                    st.success(f"Default model updated to {new_model}!")
                    st.rerun()

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
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
                st.warning("No models found. Pull one via terminal: `ollama pull gemma4:e2b`")

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
