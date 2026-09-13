"""
SQLite database layer.

Handles: organizations (with admin-approval workflow), org users, public
(general-use) users, documents, chat_history, datasets, and external DB
connections registered by organizations.

Design note: raw text chunks + embeddings are NOT stored here — they live in
ChromaDB (see rag.py). SQL is used for structured, relational data.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't already exist. Safe to call every run."""
    with get_conn() as conn:
        c = conn.cursor()

        # status: 'pending' (awaiting admin approval) | 'approved' | 'rejected'
        c.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            org_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_name TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(org_id)
        )""")

        # General/public-mode users - signed in with Google, or a guest session
        c.execute("""
        CREATE TABLE IF NOT EXISTS public_users (
            public_user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            auth_method TEXT DEFAULT 'guest',   -- 'google' | 'guest'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            doc_type TEXT,
            num_chunks INTEGER DEFAULT 0,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(org_id)
        )""")

        # org_id is NULL for public-mode chats; user_type distinguishes the two modes
        c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER,
            user_type TEXT NOT NULL,     -- 'public' | 'org'
            identifier TEXT,             -- email (public) or username (org)
            mode TEXT,                   -- 'general_chat' | 'rag_chat' | 'summarize' | 'text_to_sql' | 'image_analysis'
            question TEXT,
            answer TEXT,
            sources TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(org_id)
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            table_name TEXT NOT NULL,
            original_filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(org_id)
        )""")

        # Lets an org connect its OWN external database instead of uploading files
        c.execute("""
        CREATE TABLE IF NOT EXISTS db_connections (
            conn_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            db_type TEXT,                 -- 'postgresql' | 'mysql' | 'sqlite'
            connection_string TEXT,       -- NOTE: stored in plain text - see README security note
            label TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(org_id)
        )""")


# ---------------------------------------------------------------- orgs ----
def list_pending_organizations():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM organizations WHERE status='pending' ORDER BY created_at")
        return [dict(r) for r in c.fetchall()]


def list_all_organizations():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM organizations ORDER BY created_at DESC")
        return [dict(r) for r in c.fetchall()]


def set_org_status(org_id, status):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE organizations SET status=?, reviewed_at=CURRENT_TIMESTAMP WHERE org_id=?",
            (status, org_id),
        )


# ----------------------------------------------------------- documents ----
def add_document_record(org_id, filename, doc_type, num_chunks):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO documents (org_id, filename, doc_type, num_chunks) VALUES (?, ?, ?, ?)",
            (org_id, filename, doc_type, num_chunks),
        )
        return c.lastrowid


def list_documents(org_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT doc_id, filename, doc_type, num_chunks, upload_date "
            "FROM documents WHERE org_id=? ORDER BY upload_date DESC",
            (org_id,),
        )
        return [dict(r) for r in c.fetchall()]


# ------------------------------------------------------------- chat log ----
def log_chat(user_type, identifier, mode, question, answer, sources="", org_id=None):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_history (org_id, user_type, identifier, mode, question, answer, sources) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (org_id, user_type, identifier, mode, question, answer, sources),
        )


def get_org_chat_history(org_id, limit=50):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT identifier, mode, question, answer, created_at FROM chat_history "
            "WHERE org_id=? ORDER BY created_at DESC LIMIT ?",
            (org_id, limit),
        )
        return [dict(r) for r in c.fetchall()]


def get_public_chat_history(identifier, limit=50):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT mode, question, answer, created_at FROM chat_history "
            "WHERE user_type='public' AND identifier=? ORDER BY created_at DESC LIMIT ?",
            (identifier, limit),
        )
        return [dict(r) for r in c.fetchall()]


# ---------------------------------------------------------- public users ----
def upsert_public_user(email, name, auth_method="guest"):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT public_user_id FROM public_users WHERE email=?", (email,))
        row = c.fetchone()
        if row:
            c.execute(
                "UPDATE public_users SET last_login=CURRENT_TIMESTAMP, name=? WHERE email=?",
                (name, email),
            )
            return row["public_user_id"]
        c.execute(
            "INSERT INTO public_users (email, name, auth_method) VALUES (?, ?, ?)",
            (email, name, auth_method),
        )
        return c.lastrowid


# ------------------------------------------------------- db connections ----
def add_db_connection(org_id, db_type, connection_string, label):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO db_connections (org_id, db_type, connection_string, label) VALUES (?, ?, ?, ?)",
            (org_id, db_type, connection_string, label),
        )
        return c.lastrowid


def list_db_connections(org_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT conn_id, db_type, connection_string, label, added_at "
            "FROM db_connections WHERE org_id=? ORDER BY added_at DESC",
            (org_id,),
        )
        return [dict(r) for r in c.fetchall()]
