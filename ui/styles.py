"""Custom CSS styling and design components for ReplyDesk."""

import streamlit as st

CUSTOM_CSS = """
<style>
/* Modern typography and container polish */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Glassmorphism card container */
.st-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

/* Badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-green {
    background-color: #10b98125;
    color: #10b981;
    border: 1px solid #10b98150;
}
.badge-orange {
    background-color: #f59e0b25;
    color: #f59e0b;
    border: 1px solid #f59e0b50;
}
.badge-red {
    background-color: #ef444425;
    color: #ef4444;
    border: 1px solid #ef444450;
}
.badge-blue {
    background-color: #3b82f625;
    color: #3b82f6;
    border: 1px solid #3b82f650;
}
.badge-purple {
    background-color: #8b5cf625;
    color: #8b5cf6;
    border: 1px solid #8b5cf650;
}

/* Chat bubble styling for customer simulator */
.chat-bubble-customer {
    background: #3b82f615;
    border: 1px solid #3b82f640;
    border-radius: 14px 14px 2px 14px;
    padding: 12px 16px;
    margin: 8px 0;
    max-width: 80%;
    margin-left: auto;
    text-align: right;
}
.chat-bubble-shop {
    background: #10b98115;
    border: 1px solid #10b98140;
    border-radius: 14px 14px 14px 2px;
    padding: 12px 16px;
    margin: 8px 0;
    max-width: 80%;
    margin-right: auto;
    text-align: left;
}
.chat-meta {
    font-size: 0.72rem;
    opacity: 0.7;
    margin-top: 4px;
}

/* Simulation disclaimer banner */
.demo-banner {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.15));
    border: 1px dashed rgba(168, 85, 247, 0.4);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.85rem;
    color: #c084fc;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Warning alert boxes */
.alert-warning-box {
    background-color: #fef3c715;
    border-left: 4px solid #f59e0b;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    font-size: 0.88rem;
}
.alert-danger-box {
    background-color: #fee2e215;
    border-left: 4px solid #ef4444;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    font-size: 0.88rem;
}
</style>
"""


def apply_custom_styles():
    """Inject custom CSS for refined visual aesthetics."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
