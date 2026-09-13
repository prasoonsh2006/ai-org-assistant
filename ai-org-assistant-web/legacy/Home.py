"""
Landing page for the site. Run with:  streamlit run Home.py

Presents the two modes:
  1. Public / General Use  -> pages/1_Public_Assistant.py
  2. Organization Portal    -> pages/2_Organization_Login.py
"""

import streamlit as st
import database
from ui import inject_base_style, site_header

st.set_page_config(page_title="AI Data Assistant", page_icon="🤖", layout="wide")
database.init_db()
inject_base_style()

site_header(
    "AI Data Assistant",
    "One platform, two modes: a free general-purpose AI assistant for everyone, "
    "and a private analytics workspace for registered organizations.",
)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(
        """<div class="mode-card">
        <h3>🌐 General / Public Use</h3>
        <p>Chat with an AI assistant just like ChatGPT or Gemini. Sign in with
        Google (or continue as a guest) - no registration or approval needed.</p>
        <ul>
            <li>Ask anything - general knowledge, writing help, coding, etc.</li>
            <li>Upload an <b>image</b> and ask questions about it</li>
            <li>Upload a <b>PDF / Word / text file</b> and get a summary or ask questions</li>
        </ul>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("Go to Public Assistant →", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Public_Assistant.py")

with col2:
    st.markdown(
        """<div class="mode-card">
        <h3>🏢 For Organizations</h3>
        <p>Register your organization to analyze your own private data -
        documents, spreadsheets, or a live database connection.</p>
        <ul>
            <li>Registration requires <b>admin approval</b> before login works</li>
            <li>Upload files, or <b>connect your own database</b> directly</li>
            <li>Chat with your documents, get summaries, run natural-language analytics</li>
        </ul>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("Go to Organization Portal →", use_container_width=True):
        st.switch_page("pages/2_Organization_Login.py")

st.divider()
st.caption("Are you an administrator? Use the Admin Panel page in the sidebar to review organization signups.")
