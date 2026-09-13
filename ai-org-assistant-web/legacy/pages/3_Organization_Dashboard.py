"""
Organization dashboard - only reachable once logged in (auth.login already
enforces the org is 'approved'). Lets the org upload documents/datasets OR
connect its own external database, then chat/summarize/analyze.
"""

import json
import streamlit as st
import pandas as pd
import plotly.express as px

import database
import ingestion
import rag
import llm
import text_to_sql
import external_db
from ui import inject_base_style, site_header

st.set_page_config(page_title="Organization Dashboard", page_icon="🏢", layout="wide")
database.init_db()
inject_base_style()

if "org_user" not in st.session_state or st.session_state.org_user is None:
    st.warning("Please log in first.")
    st.stop()

user = st.session_state.org_user
org_id = user["org_id"]

with st.sidebar:
    site_header(user["org_name"], "")
    st.markdown(f"**User:** {user['username']} ({user['role']})")
    if st.button("Log out"):
        st.session_state.org_user = None
        st.rerun()
    st.divider()
    nav_options = ["📤 Upload Data", "🔌 Connect Database", "💬 Chat (RAG)", "📝 Summarize",
                    "📊 Analytics", "🕑 Chat History"]
    if user["role"] == "admin":
        nav_options.insert(5, "✏️ Update Data")
    page = st.radio("Navigate", nav_options)

st.title(f"🏢 {user['org_name']} — Analytics Workspace")


# ------------------------------------------------------------ upload page ----
if page == "📤 Upload Data":
    st.subheader("1. Documents for AI Chat & Summarization (PDF / DOCX / TXT)")
    doc_file = st.file_uploader("Upload a document", type=["pdf", "docx", "txt"], key="doc_upload")
    if doc_file is not None and st.button("Process Document"):
        with st.spinner("Extracting text, chunking, and generating embeddings..."):
            file_type = doc_file.name.rsplit(".", 1)[-1]
            text = ingestion.extract_text(doc_file.getvalue(), file_type)
            chunks = ingestion.chunk_text(text)
            if not chunks:
                st.error("Could not extract any text from this file.")
            else:
                doc_id = database.add_document_record(org_id, doc_file.name, file_type, len(chunks))
                rag.add_chunks(org_id, doc_id, doc_file.name, chunks)
                st.success(f"'{doc_file.name}' processed into {len(chunks)} chunks and indexed!")

    st.divider()
    st.subheader("2. Structured Data for Analytics (CSV / Excel)")
    data_file = st.file_uploader("Upload a spreadsheet", type=["csv", "xlsx"], key="data_upload")
    if data_file is not None and st.button("Process Dataset"):
        with st.spinner("Loading dataset into database..."):
            df = pd.read_csv(data_file) if data_file.name.endswith(".csv") else pd.read_excel(data_file)
            table_name, columns = text_to_sql.register_dataset(org_id, data_file.name, df)
            st.success(f"Dataset '{data_file.name}' loaded as table `{table_name}`.")
            st.dataframe(df.head(10))

    st.divider()
    st.subheader("📚 Your Organization's Documents")
    docs = database.list_documents(org_id)
    st.dataframe(pd.DataFrame(docs)) if docs else st.info("No documents uploaded yet.")


# --------------------------------------------------------- connect db page ----
elif page == "🔌 Connect Database":
    st.subheader("Connect Your Own Database")
    st.caption(
        "Instead of uploading files, point this at your organization's own "
        "PostgreSQL / MySQL / SQLite database and query it directly. "
        "⚠️ For security, use a **read-only** database user for this connection."
    )

    db_type = st.selectbox("Database type", ["postgresql", "mysql", "sqlite"])
    if db_type == "postgresql":
        placeholder = "postgresql://user:password@host:5432/dbname"
    elif db_type == "mysql":
        placeholder = "mysql+pymysql://user:password@host:3306/dbname"
    else:
        placeholder = "sqlite:///C:/path/to/your/database.db"

    label = st.text_input("Label for this connection (e.g. 'Sales DB')")
    conn_str = st.text_input("Connection string", placeholder=placeholder)

    if st.button("Test & Save Connection") and conn_str:
        ok, err = external_db.test_connection(conn_str)
        if ok:
            database.add_db_connection(org_id, db_type, conn_str, label or db_type)
            st.success("Connected and saved!")
        else:
            st.error(f"Connection failed: {err}")

    st.divider()
    st.subheader("Saved Connections")
    conns = database.list_db_connections(org_id)
    if not conns:
        st.info("No database connections saved yet.")
    else:
        for conn in conns:
            st.write(f"**{conn['label']}** ({conn['db_type']}) — added {conn['added_at']}")


# ------------------------------------------------------------- chat page ----
elif page == "💬 Chat (RAG)":
    question = st.text_input("Ask a question about your uploaded documents:")
    if st.button("Ask") and question.strip():
        with st.spinner("Retrieving relevant context and generating answer..."):
            results = rag.query_chunks(org_id, question)
            if not results:
                st.warning("No documents found for your organization yet. Upload some first!")
            else:
                context_chunks = [doc for doc, _ in results]
                answer = llm.generate_rag_answer(question, context_chunks)
                st.markdown("### Answer")
                st.write(answer)

                sources = sorted({meta["filename"] for _, meta in results})
                with st.expander("📎 Sources used"):
                    for doc_text, meta in results:
                        st.markdown(f"**{meta['filename']}** (chunk #{meta['chunk_index']})")
                        st.caption(doc_text[:300] + ("..." if len(doc_text) > 300 else ""))

                database.log_chat("org", user["username"], "rag_chat", question, answer,
                                   json.dumps(sources), org_id=org_id)


# --------------------------------------------------------- summarize page ----
elif page == "📝 Summarize":
    docs = database.list_documents(org_id)
    if not docs:
        st.info("No documents uploaded yet. Go to 'Upload Data' first.")
    else:
        selected = st.selectbox("Choose a document to summarize", [d["filename"] for d in docs])
        if st.button("Generate Summary"):
            with st.spinner("Retrieving document content and summarizing..."):
                all_chunks = rag.query_chunks(org_id, selected, top_k=50)
                matching = [doc for doc, meta in all_chunks if meta["filename"] == selected]
                if not matching:
                    st.error("Could not retrieve content for this document.")
                else:
                    summary = llm.summarize_text("\n\n".join(matching))
                    st.markdown("### Summary")
                    st.write(summary)
                    database.log_chat("org", user["username"], "summarize",
                                       f"Summarize: {selected}", summary, org_id=org_id)


# --------------------------------------------------------- analytics page ----
elif page == "📊 Analytics":
    source = st.radio("Data source", ["Uploaded Dataset", "Connected Database"], horizontal=True)

    if source == "Uploaded Dataset":
        datasets = text_to_sql.list_datasets(org_id)
        if not datasets:
            st.info("No datasets uploaded yet. Go to 'Upload Data' first.")
        else:
            table_options = {d["original_filename"]: d["table_name"] for d in datasets}
            selected_file = st.selectbox("Choose a dataset", list(table_options.keys()))
            table_name = table_options[selected_file]
            columns = text_to_sql.get_table_columns(table_name)
            st.caption(f"Columns: {', '.join(columns)}")

            question = st.text_input("Ask a question in plain English")
            if st.button("Run Analysis") and question.strip():
                with st.spinner("Converting your question to SQL and running it..."):
                    try:
                        sql = llm.nl_to_sql(question, table_name, columns)
                        st.code(sql, language="sql")
                        result_df = text_to_sql.run_safe_select(sql)
                        st.dataframe(result_df)

                        numeric_cols = result_df.select_dtypes(include="number").columns.tolist()
                        non_numeric_cols = [c for c in result_df.columns if c not in numeric_cols]
                        if numeric_cols and non_numeric_cols and len(result_df) > 1:
                            fig = px.bar(result_df, x=non_numeric_cols[0], y=numeric_cols[0])
                            st.plotly_chart(fig, use_container_width=True)

                        database.log_chat("org", user["username"], "text_to_sql", question, sql, org_id=org_id)
                    except Exception as e:
                        st.error(f"Could not run this query: {e}")

    else:  # Connected Database
        conns = database.list_db_connections(org_id)
        if not conns:
            st.info("No database connections yet. Go to 'Connect Database' first.")
        else:
            conn_options = {c["label"]: c for c in conns}
            selected_label = st.selectbox("Choose a connection", list(conn_options.keys()))
            conn = conn_options[selected_label]

            try:
                tables = external_db.list_tables(conn["connection_string"])
            except Exception as e:
                st.error(f"Could not list tables: {e}")
                tables = []

            if tables:
                table_name = st.selectbox("Choose a table", tables)
                columns = external_db.get_columns(conn["connection_string"], table_name)
                st.caption(f"Columns: {', '.join(columns)}")

                question = st.text_input("Ask a question in plain English", key="ext_db_q")
                if st.button("Run Analysis", key="ext_db_run") and question.strip():
                    with st.spinner("Converting your question to SQL and running it..."):
                        try:
                            sql = llm.nl_to_sql(question, table_name, columns)
                            st.code(sql, language="sql")
                            result_df = external_db.run_safe_select(conn["connection_string"], sql)
                            st.dataframe(result_df)

                            numeric_cols = result_df.select_dtypes(include="number").columns.tolist()
                            non_numeric_cols = [c for c in result_df.columns if c not in numeric_cols]
                            if numeric_cols and non_numeric_cols and len(result_df) > 1:
                                fig = px.bar(result_df, x=non_numeric_cols[0], y=numeric_cols[0])
                                st.plotly_chart(fig, use_container_width=True)

                            database.log_chat("org", user["username"], "text_to_sql", question, sql, org_id=org_id)
                        except Exception as e:
                            st.error(f"Could not run this query: {e}")


# ------------------------------------------------------- update data page ----
elif page == "✏️ Update Data":
    st.caption(
        "Update or add records using plain English "
        "(e.g. *\"update Rahul's marks to 30\"* or *\"add a new student named Priya with marks 85\"*). "
        "**Restricted to admins.** Nothing is changed until you review and confirm it below."
    )
    source = st.radio("Data source", ["Uploaded Dataset", "Connected Database"], horizontal=True, key="write_source")

    if source == "Uploaded Dataset":
        datasets = text_to_sql.list_datasets(org_id)
        if not datasets:
            st.info("No datasets uploaded yet. Go to 'Upload Data' first.")
        else:
            table_options = {d["original_filename"]: d["table_name"] for d in datasets}
            selected_file = st.selectbox("Choose a dataset", list(table_options.keys()), key="write_ds")
            table_name = table_options[selected_file]
            columns = text_to_sql.get_table_columns(table_name)
            st.caption(f"Columns: {', '.join(columns)}")

            instruction = st.text_input("What do you want to update or add?", key="write_instr")
            if st.button("Preview Change") and instruction.strip():
                with st.spinner("Converting your instruction to SQL..."):
                    sql = llm.nl_to_write_sql(instruction, table_name, columns)
                    st.session_state["pending_write_sql"] = sql
                    st.session_state["pending_write_table"] = table_name
                    st.session_state["pending_write_target"] = "dataset"

            pending_sql = st.session_state.get("pending_write_sql")
            if pending_sql and st.session_state.get("pending_write_target") == "dataset":
                st.code(pending_sql, language="sql")
                try:
                    if pending_sql.strip().lower().startswith("update"):
                        preview_df = text_to_sql.preview_affected_rows(table_name, pending_sql)
                        st.write(f"**{len(preview_df)} row(s) will be affected:**")
                        st.dataframe(preview_df)
                    else:
                        st.write("This will **insert a new row**. Review the statement above carefully.")

                    if st.button("✅ Confirm and Apply Change"):
                        rows_affected = text_to_sql.run_safe_write(pending_sql)
                        st.success(f"Done — {rows_affected} row(s) affected.")
                        database.log_chat("org", user["username"], "text_to_sql_write",
                                           instruction, pending_sql, org_id=org_id)
                        del st.session_state["pending_write_sql"]
                except Exception as e:
                    st.error(f"Could not apply this change: {e}")

    else:  # Connected Database
        conns = database.list_db_connections(org_id)
        if not conns:
            st.info("No database connections yet. Go to 'Connect Database' first.")
        else:
            conn_options = {c["label"]: c for c in conns}
            selected_label = st.selectbox("Choose a connection", list(conn_options.keys()), key="write_conn")
            conn = conn_options[selected_label]

            try:
                tables = external_db.list_tables(conn["connection_string"])
            except Exception as e:
                st.error(f"Could not list tables: {e}")
                tables = []

            if tables:
                table_name = st.selectbox("Choose a table", tables, key="write_ext_table")
                columns = external_db.get_columns(conn["connection_string"], table_name)
                st.caption(f"Columns: {', '.join(columns)}")

                instruction = st.text_input("What do you want to update or add?", key="write_ext_instr")
                if st.button("Preview Change", key="write_ext_preview") and instruction.strip():
                    with st.spinner("Converting your instruction to SQL..."):
                        sql = llm.nl_to_write_sql(instruction, table_name, columns)
                        st.session_state["pending_write_sql"] = sql
                        st.session_state["pending_write_table"] = table_name
                        st.session_state["pending_write_target"] = "external"
                        st.session_state["pending_write_conn"] = conn["connection_string"]

                pending_sql = st.session_state.get("pending_write_sql")
                if pending_sql and st.session_state.get("pending_write_target") == "external":
                    st.code(pending_sql, language="sql")
                    try:
                        if pending_sql.strip().lower().startswith("update"):
                            preview_df = external_db.preview_affected_rows(
                                st.session_state["pending_write_conn"], table_name, pending_sql)
                            st.write(f"**{len(preview_df)} row(s) will be affected:**")
                            st.dataframe(preview_df)
                        else:
                            st.write("This will **insert a new row**. Review the statement above carefully.")

                        if st.button("✅ Confirm and Apply Change", key="write_ext_confirm"):
                            rows_affected = external_db.run_safe_write(
                                st.session_state["pending_write_conn"], pending_sql)
                            st.success(f"Done — {rows_affected} row(s) affected.")
                            database.log_chat("org", user["username"], "text_to_sql_write",
                                               instruction, pending_sql, org_id=org_id)
                            del st.session_state["pending_write_sql"]
                    except Exception as e:
                        st.error(f"Could not apply this change: {e}")


# ----------------------------------------------------------- history page ----
elif page == "🕑 Chat History":
    history = database.get_org_chat_history(org_id)
    st.dataframe(pd.DataFrame(history)) if history else st.info("No activity yet.")
