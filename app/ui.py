import json
import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("SEARCHSAGE_BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="SearchSage")
st.title("SearchSage")
st.caption("Ask a question, SearchSage grounds the answer in live information when it needs to.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    try:
        resp = requests.post(f"{BACKEND_URL}/session", timeout=10)
        resp.raise_for_status()
        st.session_state.session_id = resp.json().get("session_id")
    except requests.RequestException:
        st.session_state.session_id = None

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("Hello. Ask me anything, I will pull in live information when the question needs it.")


def send_feedback(answer_id: str, vote: str) -> None:
    try:
        requests.post(f"{BACKEND_URL}/feedback", json={"answer_id": answer_id, "vote": vote}, timeout=10)
    except requests.RequestException:
        pass


def render_assistant_extras(message: dict) -> None:
    if message.get("mode"):
        label = "Live information" if message["mode"] == "live" else "General knowledge"
        st.caption(label)

    if message.get("sources"):
        with st.expander("Sources"):
            for src in message["sources"]:
                st.markdown(f"- [{src}]({src})")

    answer_id = message.get("answer_id")
    if not answer_id:
        return

    voted_key = f"voted_{answer_id}"
    already_voted = st.session_state.get(voted_key)
    col1, col2, col3 = st.columns([1, 1, 6])
    with col1:
        if st.button("Up", key=f"up_{answer_id}", disabled=bool(already_voted)):
            send_feedback(answer_id, "up")
            st.session_state[voted_key] = "up"
    with col2:
        if st.button("Down", key=f"down_{answer_id}", disabled=bool(already_voted)):
            send_feedback(answer_id, "down")
            st.session_state[voted_key] = "down"
    with col3:
        st.markdown(f"[Share link]({BACKEND_URL}/answer/{answer_id})")


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_assistant_extras(msg)

user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    answer_text = ""
    sources: list[str] = []
    mode = None
    answer_id = None
    error_message = None

    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Thinking..."):
            try:
                response = requests.get(
                    f"{BACKEND_URL}/query/stream",
                    params={"question": user_input, "session_id": st.session_state.session_id},
                    stream=True,
                    timeout=60,
                )
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    payload = json.loads(line[len("data: "):])
                    if "chunk" in payload:
                        answer_text += payload["chunk"]
                        placeholder.markdown(answer_text)
                    elif payload.get("done"):
                        sources = payload.get("sources", [])
                        mode = payload.get("mode")
                        answer_id = payload.get("answer_id")
            except requests.RequestException as exc:
                error_message = f"Could not reach SearchSage right now. {exc}"

        if error_message:
            placeholder.empty()
            st.error(error_message)
        else:
            placeholder.markdown(answer_text or "No answer returned.")
            new_message = {
                "role": "assistant",
                "content": answer_text or "No answer returned.",
                "sources": sources,
                "mode": mode,
                "answer_id": answer_id,
            }
            render_assistant_extras(new_message)
            st.session_state.messages.append(new_message)

    if error_message:
        st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": [], "mode": None, "answer_id": None})

if st.session_state.messages:
    export_lines = []
    for msg in st.session_state.messages:
        prefix = "**You:**" if msg["role"] == "user" else "**SearchSage:**"
        export_lines.append(f"{prefix} {msg['content']}")
    export_text = "\n\n".join(export_lines)
    st.download_button("Export conversation as Markdown", export_text, file_name="searchsage_conversation.md")
