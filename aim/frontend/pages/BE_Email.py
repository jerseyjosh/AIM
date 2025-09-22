import logging
import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
from streamlit.components.v1 import html

from aim.news.bailiwick_express_scraper import BEScraper
from aim.weather.gov_je import GovJeWeather
from aim.family_notices import FamilyNotices
from aim.news.models import NewsStory, FamilyNotice, TopImage, Advert
from aim.emailer.base import EmailBuilder

logger = logging.getLogger(__name__)

TITLE = "BE Email"
EMAIL_DATA_KEY = "email_data"
LOGGED_IN_KEY = "logged_in"
HA_CACHE_PATH = os.path.join(os.getcwd(), "ha_cache.csv")
VA_CACHE_PATH = os.path.join(os.getcwd(), "va_cache.csv")

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
class BEEmailData:
    news_stories: list[NewsStory] = field(default_factory=list)
    business_stories: list[NewsStory] = field(default_factory=list)
    sports_stories: list[NewsStory] = field(default_factory=list)
    community_stories: list[NewsStory] = field(default_factory=list)
    podcast_stories: list[NewsStory] = field(default_factory=list)
    weather: str = ""
    family_notices: list[FamilyNotice] = field(default_factory=list)
    top_image: TopImage = field(default_factory = lambda: TopImage())
    horizontal_adverts: list[Advert] = field(default_factory=list)
    vertical_adverts: list[Advert] = field(default_factory=list)
    connect_cover_image: str = ""

if EMAIL_DATA_KEY not in st.session_state:
    st.session_state[EMAIL_DATA_KEY] = BEEmailData()

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

async def get_email_data(
        num_news: int,
        num_business: int,
        num_sports: int,
        num_community: int,
        num_podcast: int,
        deaths_start: datetime,
        deaths_end: datetime,
) -> BEEmailData:
    """Fetch all data for email asynchronously"""
    news_scraper = BEScraper()
    weather_scraper = GovJeWeather()
    deaths_scraper = FamilyNotices()

    tasks = {
        "news_stories": news_scraper.get_n_stories_for_region("jsy", num_news),
        "business_stories": news_scraper.get_n_stories_for_region("jsy_business", num_business),
        "sports_stories": news_scraper.get_n_stories_for_region("jsy_sport", num_sports),
        "community_stories": news_scraper.get_n_stories_for_region("jsy_community", num_community),
        "podcast_stories": news_scraper.get_n_stories_for_region("jsy_podcasts", num_podcast),
        "connect_cover_image": news_scraper.get_jsy_connect_cover(),
        "weather": weather_scraper.get_to_email(),
        "family_notices": deaths_scraper.get_notices(deaths_start, deaths_end)
    }
    values = await asyncio.gather(*tasks.values())
    results = dict(zip(tasks.keys(), values))
    await asyncio.gather(news_scraper.close(), deaths_scraper.close())

    params = {}
    for k,v in results.items():
        if isinstance(v, Exception):
            logger.error(f'Failed to get email data: {k}')
        else:
            params[k] = v
    return BEEmailData(**params)

async def manually_scrape_urls(urls: list[str]):
    """Manually scrape list of urls"""
    scraper = BEScraper()
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
    num_news = st.number_input("Number of News Stories", min_value=1, max_value=20, value=7, step=1)
    num_business = st.number_input("Number of Business Stories", min_value=1, max_value=20, value=1, step=1)
    num_sports = st.number_input("Number of Sports Stories", min_value=1, max_value=20, value=1, step=1)
    num_community = st.number_input("Number of Community Stories", min_value=1, max_value=20, value=1, step=1)
    num_podcast = st.number_input("Number of Podcast Stories", min_value=1, max_value=20, value=1, step=1)

    # Top image parameters
    top_image_url = st.text_input("Top Image URL")
    top_image_title = st.text_input("Top Image Title", key="top_image_title")
    top_image_author = st.text_input("Top Image Author", key="top_image_author")
    top_image_link = st.text_input("Top Image Link (Leave Blank if None)", key="top_image_link")

    # advert tables
    st.subheader("Vertical Adverts")
    vertical_adverts_df = st.data_editor(
        adverts_to_dataframe(st.session_state[EMAIL_DATA_KEY].vertical_adverts),
        key="vertical_adverts",
        num_rows="dynamic",
        width='stretch',
        hide_index=True
    )
    st.subheader("Horizontal Adverts")
    horizontal_adverts_df = st.data_editor(
        adverts_to_dataframe(st.session_state[EMAIL_DATA_KEY].horizontal_adverts),
        key="horizontal_adverts",
        num_rows="dynamic",
        width='stretch',
        hide_index=True
    )
    subcol1, subcol2, subcol3 = st.columns(3)
    with subcol1:
        if st.button("Save Adverts"):
            vertical_adverts_df.to_csv(VA_CACHE_PATH)
            horizontal_adverts_df.to_csv(HA_CACHE_PATH)
            st.success("Saved Adverts Cache")
    with subcol2:
        if st.button("Load Adverts"):
            if os.path.exists(HA_CACHE_PATH):
                print("FOUND HA CACHE")
                try:
                    hdf = pd.read_csv(HA_CACHE_PATH)
                    st.session_state[EMAIL_DATA_KEY].horizontal_adverts = df_to_adverts(hdf)
                except:
                    st.error("Couldn't load adverts cache - please report issue to josh@hakuna.co.uk")
            else:
                st.error("No horizontal adverts cache found")
            if os.path.exists(VA_CACHE_PATH):
                print("FOUND VA CACHE")
                try:
                    vdf = pd.read_csv(VA_CACHE_PATH)
                    st.session_state[EMAIL_DATA_KEY].vertical_adverts = df_to_adverts(vdf)
                except:
                    st.error("Couldn't load adverts cache - please report issue to josh@hakuna.co.uk")
            else:
                st.error("No vertical adverts cache found")
            st.rerun()
    with subcol3:
        if st.button("Delete Adverts Cache (For if anything weird happens)"):
            for path in [HA_CACHE_PATH, VA_CACHE_PATH]:
                if os.path.exists(path):
                    os.remove(path)
            st.success("Deleted cache")

    # deaths start/end
    deaths_start = st.date_input("Deaths Start Date", value = datetime.today().date() - timedelta(days=1))
    deaths_end = st.date_input("Deaths End Date", value = datetime.today().date())

    # fetch data button
    stories = []
    if st.button("Fetch"):
        with st.spinner("Fetching stories"):
            email_data: BEEmailData = asyncio.run(get_email_data(
                num_news = num_news,
                num_business = num_business,
                num_sports = num_sports,
                num_community = num_community,
                num_podcast = num_podcast,
                deaths_start = deaths_start,
                deaths_end = deaths_end
            ))
            st.session_state[EMAIL_DATA_KEY] = email_data

    # edit story dataframes
    news_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].news_stories), key="news_stories", hide_index=True)
    business_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].business_stories), key="business_stories", hide_index=True)
    sports_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].sports_stories), key="sports_stories", hide_index=True)
    community_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].community_stories), key="community_stories", hide_index=True)
    podcast_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].podcast_stories), key="podcast_stories", hide_index=True)

    # update email data state
    st.session_state[EMAIL_DATA_KEY].news_stories = df_to_stories(news_df)
    st.session_state[EMAIL_DATA_KEY].business_stories = df_to_stories(business_df)
    st.session_state[EMAIL_DATA_KEY].sports_stories = df_to_stories(sports_df)
    st.session_state[EMAIL_DATA_KEY].community_stories = df_to_stories(community_df)
    st.session_state[EMAIL_DATA_KEY].podcast_stories = df_to_stories(podcast_df)
    st.session_state[EMAIL_DATA_KEY].top_image = TopImage(
        title=top_image_title,
        url = top_image_url,
        author = top_image_author,
        link = top_image_link
    )
    st.session_state[EMAIL_DATA_KEY].vertical_adverts = df_to_adverts(vertical_adverts_df)
    st.session_state[EMAIL_DATA_KEY].horizontal_adverts = df_to_adverts(horizontal_adverts_df)

    # Manual URL Input Section
    st.title("Add Stories Manually")
    story_type = st.selectbox("Add to", ["news_stories", "business_stories", "sports_stories", "community_stories", "podcast_stories"], key="manual_url_type")
    manual_urls = st.text_area("Enter URLs (one per line)", key="manual_urls")
    if st.button("Process URLs") and manual_urls:
        urls = [url.strip() for url in manual_urls.split("\n") if url.strip()]
        with st.spinner(f"Processing {len(urls)} URLs..."):
            # run async function in sync context
            new_stories: list[NewsStory] = asyncio.run(manually_scrape_urls(urls))
            # Get current stories and add new ones
            current_stories = getattr(st.session_state[EMAIL_DATA_KEY], story_type)
            new_stories = current_stories + new_stories
            # update email data
            setattr(st.session_state[EMAIL_DATA_KEY], story_type, new_stories)
            st.success(f"Added {len(stories)} stories to {story_type}")
            st.rerun()

with col2:

    if len(st.session_state[EMAIL_DATA_KEY].news_stories) > 0:
        rendered_html = EmailBuilder.BE().render(st.session_state[EMAIL_DATA_KEY])
        html(rendered_html, scrolling=True, height=2000)

        if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
            st.success("Email saved successfully")