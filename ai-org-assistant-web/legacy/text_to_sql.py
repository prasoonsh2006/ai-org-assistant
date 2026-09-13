"""
Text-to-SQL for an organization's OWN uploaded datasets (CSV/Excel -> SQLite
table). Supports both READ (SELECT) and WRITE (UPDATE/INSERT) natural
language queries.

Safety model for writes:
1. The LLM is instructed to only ever produce UPDATE or INSERT (never
   DELETE/DROP/ALTER/TRUNCATE) - see llm.nl_to_write_sql.
2. run_safe_write() re-checks this at execution time regardless of what the
   LLM produced - a hardcoded blocklist, not just a prompt instruction.
3. For UPDATEs, preview_affected_rows() shows exactly which rows will change
   BEFORE anything is committed, so the UI can ask for explicit confirmation.
"""

import re
import sqlite3
import pandas as pd

from database import DB_PATH, get_conn

READ_FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "attach", "pragma", "--", ";"]
WRITE_FORBIDDEN = ["delete", "drop", "alter", "truncate", "attach", "pragma", "--", ";"]


def _safe_table_name(org_id: int, filename: str) -> str:
    base = re.sub(r"\W+", "_", filename.rsplit(".", 1)[0]).lower().strip("_")
    return f"org{org_id}_{base}"[:60]


def register_dataset(org_id: int, filename: str, df: pd.DataFrame):
    table_name = _safe_table_name(org_id, filename)
    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    finally:
        conn.close()

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO datasets (org_id, table_name, original_filename) VALUES (?, ?, ?)",
            (org_id, table_name, filename),
        )
    return table_name, list(df.columns)


def list_datasets(org_id: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT dataset_id, table_name, original_filename, uploaded_at "
            "FROM datasets WHERE org_id = ? ORDER BY uploaded_at DESC",
            (org_id,),
        )
        return [dict(r) for r in c.fetchall()]


def get_table_columns(table_name: str) -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info('{table_name}')")
        return [row[1] for row in cur.fetchall()]
    finally:
        conn.close()


# ------------------------------------------------------------------ read ----
def run_safe_select(sql: str) -> pd.DataFrame:
    cleaned = sql.strip().lower()
    if not cleaned.startswith("select"):
        raise ValueError("Only SELECT queries are allowed for safety.")
    if any(word in cleaned for word in READ_FORBIDDEN):
        raise ValueError("Query contains a forbidden keyword and was blocked.")

    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


# ----------------------------------------------------------------- write ----
def _extract_where_clause(sql: str) -> str | None:
    match = re.search(r"\bWHERE\b(.*)", sql, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def preview_affected_rows(table_name: str, sql: str) -> pd.DataFrame:
    """For an UPDATE statement, shows the rows that currently match its WHERE
    clause - i.e. exactly what's about to change - before anything runs."""
    where_clause = _extract_where_clause(sql)
    if not where_clause:
        raise ValueError("Refusing to preview: this UPDATE has no WHERE clause "
                          "(it would affect every row). Please be more specific.")
    preview_sql = f"SELECT * FROM {table_name} WHERE {where_clause}"
    return run_safe_select(preview_sql)


def run_safe_write(sql: str) -> int:
    """Executes an UPDATE or INSERT statement. Returns number of rows affected.
    Raises if the statement isn't UPDATE/INSERT or contains a forbidden keyword."""
    cleaned = sql.strip().lower()
    if not (cleaned.startswith("update") or cleaned.startswith("insert")):
        raise ValueError("Only UPDATE or INSERT statements are allowed here.")
    if any(word in cleaned for word in WRITE_FORBIDDEN):
        raise ValueError("Statement contains a forbidden keyword and was blocked.")
    if cleaned.startswith("update") and "where" not in cleaned:
        raise ValueError("Refusing to run an UPDATE with no WHERE clause "
                          "(it would affect every row in the table).")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
