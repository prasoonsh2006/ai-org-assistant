"""
Public / general-use mode - like ChatGPT/Gemini.
Sign in with Google (if configured) or continue as a guest. No approval
needed. Supports general chat, image analysis, and quick document Q&A/summary.
"""

import streamlit as st
import database
import auth
import llm
import ingestion
from google_auth import google_login_available, get_authenticator
from ui import inject_base_style, site_header

st.set_page_config(page_title="Public Assistant", page_icon="🌐", layout="wide")
database.init_db()
inject_base_style()

if "public_user" not in st.session_state:
    st.session_state.public_user = None
if "public_chat" not in st.session_state:
    st.session_state.public_chat = []  # list of {question, answer}


def render_login():
    site_header("General AI Assistant", "Sign in to start chatting - it's free and open to anyone.")

    if google_login_available():
        authenticator = get_authenticator()
        authenticator.check_authentification()  # yes, misspelled in the library itself
        if st.session_state.get("connected"):
            info = st.session_state["user_info"]
            user = auth.google_login_success(info.get("email"), info.get("name", info.get("email")))
            st.session_state.public_user = user
            st.rerun()
        else:
            authenticator.login()
            st.divider()
    else:
        st.info(
            "Google Sign-In isn't configured on this server yet "
            "(missing `google_credentials.json` - see README.md). "
            "You can still continue as a guest below."
        )

    with st.form("guest_form"):
        st.write("**Continue as Guest**")
        name = st.text_input("Your name")
        submitted = st.form_submit_button("Continue")
    if submitted:
        st.session_state.public_user = auth.guest_login(name)
        st.rerun()


def render_assistant():
    user = st.session_state.public_user
    site_header("General AI Assistant", f"Welcome, {user['name']}!")

    with st.sidebar:
        st.markdown(f"**Signed in as:** {user['name']}")
        st.caption(f"({user['auth_method']})")
        if st.button("Log out"):
            st.session_state.public_user = None
            st.session_state.public_chat = []
            st.rerun()

    tab_chat, tab_generate, tab_image, tab_doc = st.tabs(
        ["💬 Chat", "🎨 Generate Image", "🖼️ Analyze Image", "📄 Analyze Document"]
    )

    # ---------------- general chat ----------------
    with tab_chat:
        for turn in st.session_state.public_chat:
            with st.chat_message("user"):
                st.write(turn["question"])
            with st.chat_message("assistant"):
                st.write(turn["answer"])

        prompt = st.chat_input("Ask me anything...")
        if prompt:
            with st.chat_message("user"):
                st.write(prompt)
            with st.spinner("Thinking..."):
                answer = llm.general_chat(prompt, st.session_state.public_chat)
            with st.chat_message("assistant"):
                st.write(answer)
            st.session_state.public_chat.append({"question": prompt, "answer": answer})
            database.log_chat("public", user["email"], "general_chat", prompt, answer)

    # ---------------- image generation ----------------
    with tab_generate:
        gen_prompt = st.text_area(
            "Describe the image you want to create",
            placeholder="A serene mountain landscape at sunset, digital painting style",
        )
        if st.button("Generate Image") and gen_prompt.strip():
            with st.spinner("Generating image..."):
                try:
                    image_bytes = llm.generate_image(gen_prompt)
                    st.image(image_bytes, caption=gen_prompt, width=450)
                    st.download_button("Download Image", data=image_bytes,
                                        file_name="generated_image.png", mime="image/png")
                    database.log_chat("public", user["email"], "image_generation", gen_prompt, "(image generated)")
                except Exception as e:
                    st.error(str(e))

    # ---------------- image analysis ----------------
    with tab_image:
        image_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "webp"])
        image_question = st.text_input(
            "What do you want to know about this image?",
            value="Describe this image in detail.",
            key="img_q",
        )
        if image_file is not None:
            st.image(image_file, width=350)
            if st.button("Analyze Image"):
                with st.spinner("Analyzing image..."):
                    try:
                        answer = llm.analyze_image(image_file.getvalue(), image_question)
                        st.markdown("### Result")
                        st.write(answer)
                        database.log_chat("public", user["email"], "image_analysis", image_question, answer)
                    except Exception as e:
                        st.error(str(e))

    # ---------------- document analysis ----------------
    with tab_doc:
        doc_file = st.file_uploader("Upload a PDF, DOCX, or TXT file", type=["pdf", "docx", "txt"])
        action = st.radio("What would you like to do?", ["Summarize it", "Ask a question about it"], horizontal=True)
        doc_question = ""
        if action == "Ask a question about it":
            doc_question = st.text_input("Your question about this document")

        if doc_file is not None and st.button("Run"):
            with st.spinner("Reading document..."):
                file_type = doc_file.name.rsplit(".", 1)[-1]
                text = ingestion.extract_text(doc_file.getvalue(), file_type)

                if not text.strip():
                    st.error("Could not extract any text from this file.")
                else:
                    if action == "Summarize it":
                        answer = llm.summarize_text(text)
                        mode = "summarize"
                        logged_q = f"Summarize: {doc_file.name}"
                    else:
                        # Simple approach for a single ad-hoc file: stuff the
                        # (truncated) text directly as context - no need for a
                        # full vector DB for a one-off public-mode file.
                        answer = llm.generate_rag_answer(doc_question, [text[:12000]])
                        mode = "rag_chat"
                        logged_q = doc_question

                    st.markdown("### Result")
                    st.write(answer)
                    database.log_chat("public", user["email"], mode, logged_q, answer)


if st.session_state.public_user is None:
    render_login()
else:
    render_assistant()
