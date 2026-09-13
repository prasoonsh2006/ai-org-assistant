"""
Organization login/registration page. New organizations start 'pending' and
must be approved in the Admin Panel before their users can log in.
"""

import streamlit as st
import database
import auth
from ui import inject_base_style, site_header

st.set_page_config(page_title="Organization Portal", page_icon="🏢", layout="wide")
database.init_db()
inject_base_style()

if "org_user" not in st.session_state:
    st.session_state.org_user = None

if st.session_state.org_user is not None:
    st.switch_page("pages/3_Organization_Dashboard.py")

site_header("Organization Portal", "Register your organization or log in to your analytics workspace.")

tab_login, tab_new_org, tab_join_org = st.tabs(
    ["🔑 Login", "🏢 Register New Organization", "➕ Join Existing Organization"]
)

with tab_login:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        user, err = auth.login(username, password)
        if err:
            st.error(err)
        else:
            st.session_state.org_user = user
            st.rerun()

with tab_new_org:
    st.write("This creates a new organization and makes you its admin. "
             "**An administrator must approve it before you can log in.**")
    with st.form("new_org_form"):
        org_name = st.text_input("Organization name")
        username = st.text_input("Choose a username", key="new_org_user")
        password = st.text_input("Choose a password", type="password", key="new_org_pass")
        submitted = st.form_submit_button("Submit for Approval")
    if submitted:
        org_id, user_id, err = auth.register_org_and_admin(org_name, username, password)
        if err:
            st.error(err)
        else:
            st.success(
                f"Registration for '{org_name}' submitted! "
                "You'll be able to log in once an admin approves it."
            )

with tab_join_org:
    st.write("Join an organization that's already registered (approved or still pending).")
    with st.form("join_org_form"):
        org_name = st.text_input("Existing organization name")
        username = st.text_input("Choose a username", key="join_org_user")
        password = st.text_input("Choose a password", type="password", key="join_org_pass")
        submitted = st.form_submit_button("Join Organization")
    if submitted:
        user_id, err = auth.join_existing_organization(org_name, username, password)
        if err:
            st.error(err)
        else:
            st.success("Account created! You can log in once your organization is approved.")
