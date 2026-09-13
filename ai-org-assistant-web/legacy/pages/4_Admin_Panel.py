"""
Admin panel - review and approve/reject pending organization registrations.
Gated by a single ADMIN_PASSWORD set in .env (see config.py / README.md).
"""

import streamlit as st
import pandas as pd
import database
import auth
from ui import inject_base_style, site_header, status_badge

st.set_page_config(page_title="Admin Panel", page_icon="🛡️", layout="wide")
database.init_db()
inject_base_style()

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

site_header("Admin Panel", "Review organization sign-ups before they can access the platform.")

if not st.session_state.is_admin:
    with st.form("admin_login"):
        pw = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        ok, err = auth.admin_login(pw)
        if ok:
            st.session_state.is_admin = True
            st.rerun()
        else:
            st.error(err)
    st.stop()

if st.sidebar.button("Log out (admin)"):
    st.session_state.is_admin = False
    st.rerun()

st.subheader("⏳ Pending Approvals")
pending = database.list_pending_organizations()
if not pending:
    st.info("No pending organizations right now.")
else:
    for org in pending:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.markdown(f"**{org['org_name']}** — registered {org['created_at']}")
        if col2.button("✅ Approve", key=f"approve_{org['org_id']}"):
            database.set_org_status(org["org_id"], "approved")
            st.rerun()
        if col3.button("❌ Reject", key=f"reject_{org['org_id']}"):
            database.set_org_status(org["org_id"], "rejected")
            st.rerun()

st.divider()
st.subheader("📋 All Organizations")
all_orgs = database.list_all_organizations()
if all_orgs:
    df = pd.DataFrame(all_orgs)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No organizations registered yet.")
