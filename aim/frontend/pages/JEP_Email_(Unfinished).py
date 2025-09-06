import logging
import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime

import streamlit as st
import pandas as pd
from streamlit.components.v1 import html

from aim.news.jep_scraper import JEPScraper
from aim.emailer.base import EmailBuilder
from aim.news.models import NewsStory, Advert
from aim.emailer.base import EmailBuilder

logger = logging.getLogger(__name__)

TITLE = "JEP Email"
EMAIL_DATA_KEY = "email_data"
LOGGED_IN_KEY = "logged_in"
ADVERT_CACHE_PATH = os.path.join(os.getcwd(), "jep_ad_cache.csv")

if LOGGED_IN_KEY not in st.session_state:
    st.session_state[LOGGED_IN_KEY] = False

st.set_page_config(layout="wide")

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

@dataclass
class JEPEmailData:
    news_stories: list[NewsStory] = field(default_factory=list)
    adverts: list[Advert] = field(default_factory=list)
    jep_cover: str = ""
    publication: str = ""
    date: str = datetime.today().date().strftime("%A %-d %B %Y")

if EMAIL_DATA_KEY not in st.session_state:
    st.session_state[EMAIL_DATA_KEY] = JEPEmailData()

def stories_to_dataframe(stories: list[NewsStory]) -> pd.DataFrame:
    data = []
    for s in stories:
        data.append({
            "order": s.order,
            "headline": s.headline,
            "text": s.text,
            "author": s.author,
            "date": s.date,
            "url": s.url,
            "image_url": s.image_url,
        })
    df =  pd.DataFrame(data)
    if 'order' in df.columns:
        df.sort_values('order', inplace=True)
    return df

def df_to_stories(df: pd.DataFrame) -> list[NewsStory]:
    stories = []
    if 'order' not in df.columns:
        df['order'] = 0
    for _, row in df.sort_values('order').iterrows():
        stories.append(NewsStory(
            order=row.get("order", 0),
            headline=row["headline"],
            date=row["date"],
            author=row["author"],
            text=row["text"],
            url=row["url"],
            image_url=row["image_url"],
        ))
    return stories

def adverts_to_dataframe(adverts: list[Advert]) -> pd.DataFrame:
    data = []
    for a in adverts:
        data.append({
            'order': a.order,
            "url": a.url,
            "image_url": a.image_url
        })
    df = pd.DataFrame(data, columns=Advert.__annotations__)
    if 'order' in df.columns:
        df.sort_values('order', inplace=True)
    return df

def df_to_adverts(df: pd.DataFrame) -> list[Advert]:
    adverts = []
    if 'order' not in df.columns:
        df['order'] = 0
    for _,row in df.sort_values('order').iterrows():
        adverts.append(Advert(
            url = row['url'],
            image_url = row['image_url']
        ))
    return adverts

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

async def manually_scrape_urls(urls: list[str]):
    """Manually scrape list of urls"""
    scraper = JEPScraper()
    stories = await scraper.fetch_and_parse_stories(urls)
    await scraper.close()
    return [s for s in stories if s and not isinstance(s, Exception)]

# ---------------------------
# Main Page Layout
# ---------------------------

st.title(TITLE)

col1, col2 = st.columns(2)

with col1:

    # Input boxes for email parameters
    num_stories = st.number_input("Number of News Stories", min_value=1, max_value=20, value=7, step=1)
    num_business_stories = st.number_input("Number of Business Stories", min_value=1, max_value=20, value=1, step=1)
    num_sports_stories = st.number_input("Number of Sports Stories", min_value=1, max_value=20, value=1, step=1)
    publication = st.selectbox("Select publication section source", options=[x for x in JEPScraper.JEPCoverSource])

        # advert tables
    st.subheader("Vertical Adverts")
    adverts_df = st.data_editor(
        adverts_to_dataframe(st.session_state[EMAIL_DATA_KEY].adverts),
        key="vertical_adverts",
        num_rows="dynamic",
        width='stretch',
        hide_index=True
    )
    subcol1, subcol2, subcol3 = st.columns(3)
    with subcol1:
        if st.button("Save Adverts"):
            adverts_df.to_csv(ADVERT_CACHE_PATH)
            st.success("Saved Adverts Cache")
    with subcol2:
        if st.button("Load Adverts"):
            if os.path.exists(ADVERT_CACHE_PATH):
                print("FOUND HA CACHE")
                try:
                    hdf = pd.read_csv(ADVERT_CACHE_PATH)
                    st.session_state[EMAIL_DATA_KEY].adverts = df_to_adverts(hdf)
                except:
                    st.error("Couldn't load adverts cache")
            else:
                st.error("No horizontal adverts cache found")
            st.rerun()
    with subcol3:
        if st.button("Delete Adverts Cache (For if anything weird happens)"):
            for path in [ADVERT_CACHE_PATH]:
                if os.path.exists(path):
                    os.remove(path)
            st.success("Deleted cache")


    stories = []
    if st.button("Fetch"):
        with st.spinner("Fetching stories"):
            jep_email_data = asyncio.run(get_jep_email_data(num_stories, num_business_stories, num_sports_stories, publication))
            st.session_state[EMAIL_DATA_KEY] = jep_email_data

    news_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].news_stories), key="news_stories")
    # business_df = st.data_editor(stories_to_dataframe(st.session_state['jep_email_data'].business_stories), key="business_stories")
    # sports_df = st.data_editor(stories_to_dataframe(st.session_state['jep_email_data'].sports_stories), key="sports_stories")
    st.session_state[EMAIL_DATA_KEY].news_stories = df_to_stories(news_df)

with col2:
    
    rendered_html = EmailBuilder.JEP().render(st.session_state[EMAIL_DATA_KEY])
    html(rendered_html, scrolling=True, height=1000)

    if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
        st.success("Email saved successfully")