"""
Authentication for BOTH modes:

1. Organization mode: org registers -> status='pending' -> an admin must
   approve it in the Admin Panel before any user under that org can log in.
2. Public/general mode: sign in with Google (real OAuth, see google_auth.py)
   or continue as a guest (just a display name, no password) - no approval
   needed, this is the "anyone can use it" ChatGPT-style mode.
"""

import hashlib
import os
from database import get_conn, upsert_public_user


def _hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$")
    except ValueError:
        return False
    return _hash_password(password, salt) == stored_hash


# ------------------------------------------------------ organization mode ----
def register_organization(org_name: str):
    org_name = org_name.strip()
    if not org_name:
        return None, "Organization name cannot be empty."
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT org_id FROM organizations WHERE org_name = ?", (org_name,))
        if c.fetchone():
            return None, "An organization with this name is already registered."
        c.execute("INSERT INTO organizations (org_name, status) VALUES (?, 'pending')", (org_name,))
        return c.lastrowid, None


def register_user(org_id: int, username: str, password: str, role: str = "admin"):
    username = username.strip()
    if not username or not password:
        return None, "Username and password are required."
    if len(password) < 4:
        return None, "Password must be at least 4 characters."
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            return None, "This username is already taken."
        pw_hash = _hash_password(password)
        c.execute(
            "INSERT INTO users (org_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
            (org_id, username, pw_hash, role),
        )
        return c.lastrowid, None


def register_org_and_admin(org_name: str, username: str, password: str):
    """Creates a new organization (status='pending') plus its first admin user.
    The user CANNOT log in until the organization is approved."""
    org_id, err = register_organization(org_name)
    if err:
        return None, None, err
    user_id, err = register_user(org_id, username, password, role="admin")
    if err:
        with get_conn() as conn:
            conn.execute("DELETE FROM organizations WHERE org_id = ?", (org_id,))
        return None, None, err
    return org_id, user_id, None


def join_existing_organization(org_name: str, username: str, password: str):
    """Register a new user under an already-registered organization.
    They can only log in once that organization is approved."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT org_id FROM organizations WHERE org_name = ?", (org_name.strip(),))
        row = c.fetchone()
        if not row:
            return None, "Organization not found. Ask your admin to register it first."
        org_id = row["org_id"]
    user_id, err = register_user(org_id, username, password, role="member")
    if err:
        return None, err
    return user_id, None


def login(username: str, password: str):
    """Returns (user_dict, error). Blocks login if the org isn't approved yet."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT u.user_id, u.org_id, u.username, u.password_hash, u.role,
                      o.org_name, o.status
               FROM users u JOIN organizations o ON u.org_id = o.org_id
               WHERE u.username = ?""",
            (username,),
        )
        row = c.fetchone()
        if not row:
            return None, "No account found with that username."
        if not _verify_password(password, row["password_hash"]):
            return None, "Incorrect password."
        if row["status"] == "pending":
            return None, "Your organization's registration is still pending admin approval."
        if row["status"] == "rejected":
            return None, "Your organization's registration was not approved. Contact the admin."
        return dict(row), None


def admin_login(password: str):
    """Very simple single-admin login, gated by ADMIN_PASSWORD in .env."""
    from config import ADMIN_PASSWORD
    if not ADMIN_PASSWORD:
        return False, "ADMIN_PASSWORD is not set on the server. See README.md."
    if password == ADMIN_PASSWORD:
        return True, None
    return False, "Incorrect admin password."


# ----------------------------------------------------------- public mode ----
def guest_login(display_name: str):
    """No password, no approval - just a lightweight session for general use.
    Uses a synthetic 'email' so it fits the same public_users table as Google logins."""
    display_name = display_name.strip() or "Guest"
    synthetic_email = f"guest-{abs(hash(display_name)) % 100000}@guest.local"
    upsert_public_user(synthetic_email, display_name, auth_method="guest")
    return {"email": synthetic_email, "name": display_name, "auth_method": "guest"}


def google_login_success(email: str, name: str):
    """Called after a successful real Google OAuth login (see google_auth.py)."""
    upsert_public_user(email, name, auth_method="google")
    return {"email": email, "name": name, "auth_method": "google"}
