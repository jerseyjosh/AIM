import os
import logging
import json
import requests

import streamlit as st
from openai import OpenAI

logger = logging.getLogger(__name__)

TITLE = "Quote Extractor"

SYSTEM_PROMPT = (
    "You are a text analysis assistant. "
    "Extract the most important and key quotes from the provided text. "
    "Do not include any additional commentary, do not invent anything, only use exact quotes from the text."
    "Respond on plain text format separated by new lines. "
)

MODEL = "gpt-4.1-mini"

# ---------------------------
# Load Secrets
# ---------------------------
try:
    try:
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        STREAMLIT_USER = os.getenv("STREAMLIT_USER")
        STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")
        OPENAI_KEY = os.getenv("OPENAI_KEY")
        logger.debug("Secrets loaded from .env file")
    except Exception:
        STREAMLIT_USER = st.secrets["STREAMLIT_USER"]
        STREAMLIT_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]
        OPENAI_KEY = st.secrets["OPENAI_KEY"]
        logger.debug("Secrets loaded from Streamlit Secrets")
except Exception as e:
    logger.error("Failed to load secrets: %s", e)

if not OPENAI_KEY:
    st.error("OpenAI API key is not set. Please configure it in .env or Streamlit Secrets.")
    st.stop()

# ---------------------------
# Initialize Session State
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "openai_client" not in st.session_state:
    st.session_state["openai_client"] = OpenAI(api_key=OPENAI_KEY)

# ---------------------------
# Helpers
# ---------------------------
def make_request(client: OpenAI, text: str) -> list:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
        )
        content = response.choices[0].message.content
        return content.split("\n") if content else []
    except Exception as e:
        logger.error("Error making request to OpenAI: %s", e)
        raise

# ---------------------------
# Login
# ---------------------------
if not st.session_state["logged_in"]:
    st.title(TITLE)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == STREAMLIT_USER and password == STREAMLIT_PASSWORD:
            st.session_state["logged_in"] = True
            st.success("Logged in.")
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()

# ---------------------------
# Main Page
# ---------------------------
st.title(TITLE)
text_block = st.text_area("Paste your text here", height=300)

if st.button("Extract Key Quotes"):
    if not text_block.strip():
        st.warning("Please paste some text to extract quotes.")
    else:
        with st.spinner("Extracting quotes..."):
            try:
                client = st.session_state["openai_client"]
                quotes = make_request(client, text_block)
                st.subheader("Key Quotes")
                for i, q in enumerate(quotes, 1):
                    st.write(f"{i}. {q}")
            except Exception as e:
                st.error(f"An error occurred: {e}")
