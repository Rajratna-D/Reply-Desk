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
    page_title="ReplyDesk — Local AI Customer Assistant",
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
    except Exception as e:
        settings = None
        active_model = "Not set (set in .env)"

    # 3. Sidebar
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="font-size: 1.8rem;">🛍️</span>
                <span style="font-size: 1.4rem; font-weight: 700; letter-spacing: -0.5px;">ReplyDesk</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Local-first assistant for Instagram & WhatsApp shops.")
        st.divider()

        # Shop Selector
        conn = connect()
        try:
            sellers = list_sellers(conn)
        finally:
            conn.close()

        if not sellers:
            st.error("No shops registered in the database. Please initialize with sample configs.")
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

        st.divider()

        # Navigation
        st.markdown("**Navigation**")
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

        st.divider()

        # System health indicators
        st.markdown("**Local AI Engine**")
        if is_ollama_up:
            st.markdown(
                '<div style="font-size: 0.85rem; color: #10b981; display: flex; align-items: center; gap: 6px;">'
                '● <span style="color: inherit; font-weight: 600;">Ollama Online</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            model_installed = any(active_model in m for m in available_models)
            if model_installed:
                st.caption(f"Model: `{active_model}` (GPU offloaded)")
            else:
                st.caption(f"⚠️ Model `{active_model}` not pulled")
        else:
            st.markdown(
                '<div style="font-size: 0.85rem; color: #ef4444; display: flex; align-items: center; gap: 6px;">'
                '● <span style="color: inherit; font-weight: 600;">Ollama Offline</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        st.caption("Privacy: Runs 100% on localhost. No data sent to external servers.")

    # Top-level offline warning banner
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
