import logging
import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime

import streamlit as st
import pandas as pd
from streamlit.components.v1 import html

from aim.news.jep_scraper import JEPScraper
from aim.news.models import NewsStory
from aim.emailer.base import EmailBuilder

logger = logging.getLogger(__name__)

TITLE = "JEP Email"
EMAIL_DATA_KEY = "email_data"
LOGGED_IN_KEY = "logged_in"

if LOGGED_IN_KEY not in st.session_state:
    st.session_state[LOGGED_IN_KEY] = False

# ---------------------------
# Load Secrets
# ---------------------------
try:
    try:
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        STREAMLIT_USER = os.getenv("STREAMLIT_USER")
        STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")
        PROD = os.getenv('PROD', False)
        logger.debug("Secrets loaded from .env file")
    except Exception:
        STREAMLIT_USER = st.secrets["STREAMLIT_USER"]
        STREAMLIT_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]
        logger.debug("Secrets loaded from Streamlit Secrets")
except Exception as e:
    logger.error(f"Failed to load secrets: {e}")

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
# Helper Functions
# ---------------------------

if EMAIL_DATA_KEY not in st.session_state:
    st.session_state[EMAIL_DATA_KEY] = JEPEmailData()

def stories_to_dataframe(stories: list[NewsStory]) -> pd.DataFrame:
    data = []
    for s in stories:
        data.append({
            "Headline": s.headline,
            "Text": s.text,
            "Author": s.author,
            "Date": s.date,
            "URL": s.url,
            "Image URL": s.image_url,
        })
    return pd.DataFrame(data)

def df_to_stories(df: pd.DataFrame) -> list[NewsStory]:
    stories = []
    for _, row in df.iterrows():
        stories.append(NewsStory(
            headline=row["Headline"],
            date=row["Date"],
            author=row["Author"],
            text=row["Text"],
            url=row["URL"],
            image_url=row["Image URL"],
        ))
    return stories

async def get_jep_email_data(
        num_news: int,
        num_business: int,
        num_sports: int,
        publication: JEPScraper.JEPCoverSource
) -> JEPEmailData:
    scraper = JEPScraper()
    tasks = {
        "news_stories": scraper.get_n_stories_for_region("jsy_news", num_news),
        "business_stories": scraper.get_n_stories_for_region("jsy_business", num_business),
        "sports_stories": scraper.get_n_stories_for_region("jsy_sport", num_sports),
        "jep_cover": scraper.get_cover(JEPScraper.JEPCoverSource.Jep),
        "publication": scraper.get_cover(publication)
    }
    values = await asyncio.gather(*tasks.values())
    results = dict(zip(tasks.keys(), values))
    results['news_stories'].extend(results.pop('business_stories'))
    results['news_stories'].extend(results.pop('sports_stories'))
    results['date'] = datetime.today().date().strftime("%A %-d %B %Y")
    await scraper.close()
    return JEPEmailData(**results)

# ---------------------------
# Main Page Layout
# ---------------------------

st.title(TITLE)

# Input boxes for email parameters
num_stories = st.number_input("Number of News Stories", min_value=1, max_value=20, value=7, step=1)
num_business_stories = st.number_input("Number of Business Stories", min_value=1, max_value=20, value=1, step=1)
num_sports_stories = st.number_input("Number of Sports Stories", min_value=1, max_value=20, value=1, step=1)
publication = st.selectbox("Select publication section source", options=[x for x in JEPScraper.JEPCoverSource])

stories = []
if st.button("Fetch"):
    with st.spinner("Fetching stories"):
        jep_email_data = asyncio.run(get_jep_email_data(num_stories, num_business_stories, num_sports_stories, publication))
        st.session_state['jep_email_data'] = jep_email_data

news_df = st.data_editor(stories_to_dataframe(st.session_state['jep_email_data'].news_stories), key="news_stories")
# business_df = st.data_editor(stories_to_dataframe(st.session_state['jep_email_data'].business_stories), key="business_stories")
# sports_df = st.data_editor(stories_to_dataframe(st.session_state['jep_email_data'].sports_stories), key="sports_stories")
st.session_state[EMAIL_DATA_KEY].news_stories = df_to_stories(news_df)

rendered_html = JEPEmail().render(st.session_state[EMAIL_DATA_KEY])
st.html(rendered_html)

if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
    st.success("Email saved successfully")