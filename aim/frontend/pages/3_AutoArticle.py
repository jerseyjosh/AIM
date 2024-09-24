import os
import logging

import streamlit as st
from openai import OpenAI

logger = logging.getLogger(__name__)

TITLE = "AutoArticle"
SYSTEM_PROMPT = "You are a professional journalist that creates news articles based on a set of bullet pointed notes. Do not include information you are not given. Return unicode formatted articles in the format <headline>...</headline><text>...</text>."
FINETUNE_MODEL = "ft:gpt-4o-mini-2024-07-18:personal::AB3GrlLu"
DEFAULT_NOTES = """- Ongoing concerns over Jersey's bed blocking issues\n- Islanders facing hospital discharge delays due to carer shortages\n- Jersey Care Federation warns of 'no movement' on the issue in recent years\n- 32 patients last week unable to leave hospital despite being medically fit"""
#FINETUNE_MODEL = 'gpt-4o'

# Load Secrets
try:
    try:
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        STREAMLIT_USER = os.getenv("STREAMLIT_USER")
        STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")
        OPENAI_KEY = os.getenv("OPENAI_KEY")
        logger.debug("Secrets loaded from .env file")
    except Exception as e:
        STREAMLIT_USER = st.secrets["STREAMLIT_USER"]
        STREAMLIT_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]
        OPENAI_KEY = st.secrets["OPENAI_KEY"]
        logger.debug("Secrets loaded from Streamlit Secrets")
except Exception as e:
    logger.error("Failed to load secrets")
    logger.error(e)

# Check if the user is logged in
if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False

# Login form
if st.session_state['logged_in'] is False:
    st.title(TITLE)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == STREAMLIT_USER and password == STREAMLIT_PASSWORD:
            st.session_state['logged_in'] = True
            st.success("Logged in.")
            st.rerun()
        else:
            st.error("Invalid username or password")

else:

    def generate_article(article_notes: str, n_words: int) -> str:
        client = OpenAI(api_key=os.getenv('OPENAI_KEY'))
        user_prompt = f'write a {n_words} word news article on the following notes: {article_notes}'
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model="gpt-4o-mini"
        )
        return response.choices[0].message.content
    
    def format_article(article: str):
        """
        Convert from <headline>...</headline><text>...</text> to markdown.
        """
        article = article.replace("<headline>", "# ")
        article = article.replace("</headline>", "\n\n")
        article = article.replace("<text>", "")
        article = article.replace("</text>", "")
        return article


    # Streamlit Layout
    st.title(TITLE)

    # Textbox for article facts
    article_notes = st.text_area("Article Notes", DEFAULT_NOTES)
    # Textbox for input number of words
    n_words = st.number_input("Number of Words", value=300)

    # Button to generate article
    if st.button("Generate Article"):
        with st.spinner("Generating Article..."):
            article = generate_article(article_notes, n_words)
            formatted_article = format_article(article)
            st.session_state['article'] = formatted_article
    
    # Editable text box for article
    article_text = st.text_area("Article", value=st.session_state.get('article', ""))