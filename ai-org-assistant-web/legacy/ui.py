"""
Shared styling/header so every page of the site looks consistent - gives the
Streamlit app a cleaner, more "real website" feel instead of default styling.
"""

import streamlit as st

CUSTOM_CSS = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .main .block-container {
        padding-top: 2rem;
        max-width: 1100px;
    }

    .site-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.2rem;
    }
    .site-header h1 {
        font-size: 1.8rem;
        margin: 0;
    }
    .site-tagline {
        color: #6b7280;
        margin-bottom: 1.5rem;
        font-size: 1.05rem;
    }

    .mode-card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1.6rem;
        height: 100%;
        transition: box-shadow 0.15s ease;
    }
    .mode-card:hover {
        box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }
    .mode-card h3 {
        margin-top: 0;
    }
    .badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-pending { background:#fef3c7; color:#92400e; }
    .badge-approved { background:#d1fae5; color:#065f46; }
    .badge-rejected { background:#fee2e2; color:#991b1b; }
</style>
"""


def inject_base_style():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def site_header(title: str, tagline: str = ""):
    st.markdown(
        f"""<div class="site-header"><h1>🤖 {title}</h1></div>
        <div class="site-tagline">{tagline}</div>""",
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    css_class = {"pending": "badge-pending", "approved": "badge-approved", "rejected": "badge-rejected"}.get(status, "")
    return f'<span class="badge {css_class}">{status.upper()}</span>'
