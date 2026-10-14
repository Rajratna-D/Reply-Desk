"""ReplyDesk Streamlit application entry point."""

import streamlit as st

from engine.config import load_settings
from engine.db import connect, list_sellers
from engine.llm import ollama_status
from ui.customer_chat_page import render_customer_chat_page
from ui.history_page import render_history_page
from ui.inbox_page import render_inbox_page
from ui.reply_page import render_reply_page
from ui.settings_page import render_settings_page
from ui.setup_page import render_setup_page
from ui.styles import apply_custom_styles

st.set_page_config(
    page_title="ReplyDesk - Local AI Customer Assistant",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply refined styling
apply_custom_styles()


def main():
    # 1. Check Ollama status
    status = ollama_status()
    is_ollama_up = status["reachable"]
    available_models = status.get("models", [])

    # 2. Load settings
    try:
        settings = load_settings()
        active_model = settings.model_name
    except Exception:
        settings = None
        active_model = "gemma2:2b"

    # 3. Sidebar
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.6rem;">🛍️</span>
                    <span style="font-size: 1.3rem; font-weight: 800; letter-spacing: -0.03em; color: #f8fafc;">ReplyDesk</span>
                </div>
                <span style="font-size: 0.65rem; background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); padding: 2px 6px; border-radius: 4px; font-weight: 700; letter-spacing: 0.05em;">
                    LOCAL AI
                </span>
            </div>
            <div style="font-size: 0.78rem; color: #94a3b8; line-height: 1.35; margin-bottom: 12px;">
                Private, grounded assistant for Instagram & WhatsApp shops.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Shop Selector
        conn = connect()
        try:
            sellers = list_sellers(conn)
        finally:
            conn.close()

        if not sellers:
            st.error("No shops registered. Please initialize with sample configs.")
            active_slug = "urban_thread"
        else:
            shop_slugs = [s["slug"] for s in sellers]
            shop_names = {s["slug"]: s["shop_name"] for s in sellers}

            # Initialize session active shop
            if "active_slug" not in st.session_state or st.session_state["active_slug"] not in shop_slugs:
                st.session_state["active_slug"] = shop_slugs[0]

            selected_slug = st.selectbox(
                "Active Shop Profile:",
                options=shop_slugs,
                format_func=lambda s: f"🏪 {shop_names.get(s, s)}",
                index=shop_slugs.index(st.session_state["active_slug"]),
                help="Switching shops isolates data. Replies for one shop never use another shop's catalogue.",
            )
            st.session_state["active_slug"] = selected_slug
            active_slug = selected_slug

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # Navigation
        st.markdown(
            """
            <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;">
                WORKSPACE
            </div>
            """,
            unsafe_allow_html=True,
        )
        pages = {
            "💬 Customer Chat (Demo)": "chat",
            "📥 Owner Inbox": "inbox",
            "✍️ Manual Reply": "reply",
            "🏪 Shop Setup": "setup",
            "📜 History": "history",
            "⚙️ Settings": "settings",
        }
        nav_selection = st.radio(
            "Go to page:",
            options=list(pages.keys()),
            label_visibility="collapsed",
        )
        page_key = pages[nav_selection]

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Local Engine Status Box
        st.markdown(
            """
            <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;">
                SYSTEM TELEMETRY
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            if is_ollama_up:
                model_installed = any(active_model in m for m in available_models)
                model_note = f"<code>{active_model}</code>" if model_installed else f"⚠️ <code>{active_model}</code> not pulled"
                st.markdown(
                    f"""
                    <div style="font-size: 0.82rem; color: #34d399; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                        <span class="pulse-dot"></span> Ollama Active
                    </div>
                    <div style="font-size: 0.76rem; color: #94a3b8; margin-top: 4px;">
                        Model: {model_note}
                    </div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 2px;">
                        100% GPU Offload • RTX 3050
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div style="font-size: 0.82rem; color: #ef4444; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                        <span class="pulse-dot" style="background-color: #ef4444;"></span> Ollama Offline
                    </div>
                    <div style="font-size: 0.74rem; color: #f87171; margin-top: 3px;">
                        Run <code>ollama serve</code> in terminal
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.caption("🔒 100% On-Device Privacy. No external API calls.")

    # Offline warning banner if Ollama is down
    if not is_ollama_up:
        st.error(
            "⚠️ **Local Ollama Server is Not Running.** "
            "Please open your terminal and run `ollama serve` so ReplyDesk can generate replies locally."
        )

    # 4. Render selected page
    if page_key == "chat":
        render_customer_chat_page(active_slug)
    elif page_key == "inbox":
        render_inbox_page(active_slug)
    elif page_key == "reply":
        render_reply_page(active_slug)
    elif page_key == "setup":
        render_setup_page(active_slug)
    elif page_key == "history":
        render_history_page(active_slug)
    elif page_key == "settings":
        render_settings_page(active_slug)


if __name__ == "__main__":
    main()
