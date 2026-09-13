"""
Lets an organization connect its OWN external database (PostgreSQL, MySQL,
or another SQLite file) and query/update it directly, as an alternative to
uploading a CSV/Excel file.

Same read/write safety model as text_to_sql.py - see that file's docstring.

SECURITY NOTE (mention in your report): connection strings are stored in
plain text in app_data.db for simplicity. For real use, encrypt credentials
at rest and strongly prefer a database user with only the privileges needed
(read-only if you never intend to use the write feature).
"""

import re
import pandas as pd
from sqlalchemy import create_engine, inspect, text

READ_FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "attach", "pragma", "--", ";"]
WRITE_FORBIDDEN = ["delete", "drop", "alter", "truncate", "attach", "pragma", "--", ";"]


def test_connection(connection_string: str):
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        return False, str(e)


def list_tables(connection_string: str) -> list[str]:
    engine = create_engine(connection_string)
    return inspect(engine).get_table_names()


def get_columns(connection_string: str, table_name: str) -> list[str]:
    engine = create_engine(connection_string)
    return [col["name"] for col in inspect(engine).get_columns(table_name)]


# ------------------------------------------------------------------ read ----
def run_safe_select(connection_string: str, sql: str) -> pd.DataFrame:
    cleaned = sql.strip().lower()
    if not cleaned.startswith("select"):
        raise ValueError("Only SELECT queries are allowed for safety.")
    if any(word in cleaned for word in READ_FORBIDDEN):
        raise ValueError("Query contains a forbidden keyword and was blocked.")

    engine = create_engine(connection_string)
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)


# ----------------------------------------------------------------- write ----
def _extract_where_clause(sql: str) -> str | None:
    match = re.search(r"\bWHERE\b(.*)", sql, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def preview_affected_rows(connection_string: str, table_name: str, sql: str) -> pd.DataFrame:
    where_clause = _extract_where_clause(sql)
    if not where_clause:
        raise ValueError("Refusing to preview: this UPDATE has no WHERE clause "
                          "(it would affect every row). Please be more specific.")
    preview_sql = f"SELECT * FROM {table_name} WHERE {where_clause}"
    return run_safe_select(connection_string, preview_sql)


def run_safe_write(connection_string: str, sql: str) -> int:
    cleaned = sql.strip().lower()
    if not (cleaned.startswith("update") or cleaned.startswith("insert")):
        raise ValueError("Only UPDATE or INSERT statements are allowed here.")
    if any(word in cleaned for word in WRITE_FORBIDDEN):
        raise ValueError("Statement contains a forbidden keyword and was blocked.")
    if cleaned.startswith("update") and "where" not in cleaned:
        raise ValueError("Refusing to run an UPDATE with no WHERE clause "
                          "(it would affect every row in the table).")

    engine = create_engine(connection_string)
    with engine.begin() as conn:  # begin() auto-commits on success, rolls back on error
        result = conn.execute(text(sql))
        return result.rowcount
