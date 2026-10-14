"""Premium design system, CSS tokens, and component styling for ReplyDesk.

Customized to eliminate Streamlit prototype aesthetics and deliver a
crisp, modern SaaS workbench feel (Linear/Raycast inspired).
"""

import streamlit as st

PREMIUM_CSS = """
<style>
/* ==========================================================================
   Base Typography & Resets (Local System Font Stack - Zero External Calls)
   ========================================================================== */
html, body, [class*="css"], .stApp {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    letter-spacing: -0.015em;
    -webkit-font-smoothing: antialiased;
}

code, pre, .font-mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
}

/* Hide Streamlit default clutter */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent !important;
}
div[data-testid="stToolbar"] {
    visibility: hidden !important;
    display: none !important;
}

/* Main Background */
.stApp {
    background: radial-gradient(circle at 10% 10%, rgba(16, 185, 129, 0.035) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(99, 102, 241, 0.035) 0%, transparent 40%),
                #090d16 !important;
    color: #f1f5f9;
}

/* ==========================================================================
   Sidebar: Linear/Raycast Style Navigation
   ========================================================================== */
section[data-testid="stSidebar"] {
    background-color: #0d1322 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    gap: 0.6rem;
}

/* Convert sidebar radio buttons into sleek menu pills */
section[data-testid="stSidebar"] div[role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    background: transparent;
    border-radius: 8px;
    padding: 8px 12px;
    transition: all 0.15s ease-in-out;
    cursor: pointer;
    border: 1px solid transparent;
    margin: 0;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background: rgba(255, 255, 255, 0.04);
}

/* Hide radio circle inputs */
section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
    display: none !important;
}

/* Active sidebar item styling */
section[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"],
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background: rgba(16, 185, 129, 0.1) !important;
    border: 1px solid rgba(16, 185, 129, 0.25) !important;
    color: #34d399 !important;
    font-weight: 600;
}

/* ==========================================================================
   Containers & Card Surfaces
   ========================================================================== */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.025) 0%, rgba(255, 255, 255, 0.008) 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.35);
    transition: border-color 0.2s ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(255, 255, 255, 0.12) !important;
}

/* Custom Card Class for non-container uses */
.rd-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 14px;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.3);
}

/* ==========================================================================
   Stat & Metric Tiles
   ========================================================================== */
.stat-tile {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
}
.stat-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.15;
}
.stat-label {
    font-size: 0.72rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    margin-top: 5px;
}

/* ==========================================================================
   Badges, Tags & Indicators
   ========================================================================== */
.rd-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    font-size: 0.72rem;
    font-weight: 600;
    border-radius: 20px;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.badge-clean {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}
.badge-flagged {
    background: rgba(239, 68, 68, 0.12);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
}
.badge-warning {
    background: rgba(245, 158, 11, 0.12);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
}
.badge-model {
    background: rgba(99, 102, 241, 0.12);
    color: #a5b4fc;
    border: 1px solid rgba(99, 102, 241, 0.3);
}
.badge-lang {
    background: rgba(148, 163, 184, 0.12);
    color: #cbd5e1;
    border: 1px solid rgba(148, 163, 184, 0.25);
}

/* Pulsing Green Indicator */
.pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #10b981;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    animation: pulse-green 2s infinite;
}
@keyframes pulse-green {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* ==========================================================================
   Alert Callouts
   ========================================================================== */
.alert-card-danger {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(239, 68, 68, 0.02) 100%);
    border-left: 3px solid #ef4444;
    border-top: 1px solid rgba(239, 68, 68, 0.2);
    border-right: 1px solid rgba(239, 68, 68, 0.2);
    border-bottom: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 8px 0;
    color: #fca5a5;
    font-size: 0.86rem;
}
.alert-card-warning {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.02) 100%);
    border-left: 3px solid #f59e0b;
    border-top: 1px solid rgba(245, 158, 11, 0.2);
    border-right: 1px solid rgba(245, 158, 11, 0.2);
    border-bottom: 1px solid rgba(245, 158, 11, 0.2);
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 8px 0;
    color: #fde68a;
    font-size: 0.86rem;
}
.alert-card-success {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%);
    border-left: 3px solid #10b981;
    border-top: 1px solid rgba(16, 185, 129, 0.2);
    border-right: 1px solid rgba(16, 185, 129, 0.2);
    border-bottom: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 8px 0;
    color: #86efac;
    font-size: 0.86rem;
}

/* ==========================================================================
   Tabs Styling Overrides
   ========================================================================== */
button[data-baseweb="tab"] {
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    font-size: 0.88rem !important;
    transition: all 0.15s ease !important;
}
button[data-baseweb="tab"]:hover {
    color: #f1f5f9 !important;
    background: rgba(255, 255, 255, 0.02) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #10b981 !important;
    border-bottom: 2px solid #10b981 !important;
    font-weight: 600 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: #10b981 !important;
}

/* ==========================================================================
   Inputs & Textareas Styling
   ========================================================================== */
div[data-baseweb="input"],
div[data-baseweb="base-input"] {
    background-color: #0d1322 !important;
    border-radius: 8px !important;
}

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    background-color: #0d1322 !important;
    color: #f8fafc !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
}

div[data-baseweb="input"] input:focus,
div[data-baseweb="textarea"] textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 1px #10b981 !important;
}

/* Streamlit Selectboxes */
div[data-baseweb="select"] > div {
    background-color: #0d1322 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    color: #f8fafc !important;
}

/* ==========================================================================
   Button Styling
   ========================================================================== */
div[data-testid="stButton"] > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    padding: 6px 14px !important;
    transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Primary Button (Emerald) */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(16, 185, 129, 0.25) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35) !important;
}

/* Secondary Button (Slate Dark) */
div[data-testid="stButton"] > button[kind="secondary"],
div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {
    background: #172033 !important;
    color: #cbd5e1 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover,
div[data-testid="stButton"] > button[data-testid="baseButton-secondary"]:hover {
    background: #1e293b !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: #ffffff !important;
    transform: translateY(-1px);
}

/* ==========================================================================
   Expanders
   ========================================================================== */
div[data-testid="stExpander"] {
    background: rgba(17, 24, 39, 0.5) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 10px !important;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #e2e8f0 !important;
}

/* ==========================================================================
   Chat Simulator Styles (WhatsApp & Messenger Visuals)
   ========================================================================== */
.chat-device-frame {
    background: #0c111d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 18px;
    padding: 0;
    box-shadow: 0 12px 40px -8px rgba(0, 0, 0, 0.6);
    overflow: hidden;
}

.chat-device-header {
    background: #111827;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 12px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.chat-bubble-customer {
    background: #005c4b;
    color: #e9edef;
    border-radius: 14px 14px 2px 14px;
    padding: 10px 14px;
    max-width: 82%;
    margin-left: auto;
    margin-top: 6px;
    margin-bottom: 6px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
    font-size: 0.92rem;
    line-height: 1.38;
}

.chat-bubble-shop {
    background: #202c33;
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: #e9edef;
    border-radius: 14px 14px 14px 2px;
    padding: 10px 14px;
    max-width: 82%;
    margin-right: auto;
    margin-top: 6px;
    margin-bottom: 6px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
    font-size: 0.92rem;
    line-height: 1.38;
}

.chat-bubble-pending {
    background: rgba(245, 158, 11, 0.08);
    border: 1px dashed rgba(245, 158, 11, 0.4);
    color: #fbbf24;
    border-radius: 14px 14px 14px 2px;
    padding: 9px 13px;
    max-width: 82%;
    margin-right: auto;
    margin-top: 6px;
    margin-bottom: 6px;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Custom Scrollbars */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
}
</style>
"""


def apply_custom_styles():
    """Inject refined design styles into the Streamlit session."""
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)
