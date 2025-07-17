import streamlit as st
import requests

st.set_page_config(page_title="SearchSage")
st.title("SearchSage - Web-Scraped Chat Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Initial assistant greeting
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("Hello! Ask me anything. I will search the web and scrape real content to answer your question.")

# User input field
user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching the web and thinking..."):
            try:
                res = requests.post("http://localhost:8000/query", json={"question": user_input})
                res.raise_for_status()
                data = res.json()

                # Display assistant response
                # Separate <think> section if present
                full_answer = data.get("answer", "No answer returned.")
                if "<think>" in full_answer and "</think>" in full_answer:
                    start = full_answer.find("<think>") + len("<think>")
                    end = full_answer.find("</think>")
                    thinking = full_answer[start:end].strip()
                    answer = full_answer[end + len("</think>"):].strip()
                else:
                    thinking = None
                    answer = full_answer

                # Show main answer
                st.markdown(answer)

                # Optional: show <think> section in collapsible box
                if thinking:
                    with st.expander("Show assistant's reasoning (optional)", expanded=False):
                        st.markdown(thinking)
                # Show scraped source URLs if available
                if data.get("sources"):
                    st.markdown("**Sources scraped from the web:**")
                    for src in data["sources"]:
                        st.markdown(f"- [{src}]({src})")
                else:
                    st.markdown("_No reliable sources were found for this query._")

            except Exception as e:
                st.error(f"Error: {e}")

    st.session_state.messages.append({"role": "assistant", "content": data.get("answer", "No answer returned.")})
