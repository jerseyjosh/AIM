import os
import logging
import asyncio
import subprocess

import streamlit as st
import pandas as pd
from streamlit.components.v1 import html

from aim.emailer.base import EmailBuilder, Email, Advert
from aim.news.models import NewsStory
from aim.news import BEScraper, JEPScraper
from aim.family_notices.family_notices import FamilyNotice

logger = logging.getLogger(__name__)

TITLE = "News Email"
NEWS_SITES = ["BE", "JEP"]

# ---------------------------
# Initialize Session State
# ---------------------------

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if 'email' not in st.session_state:
    st.session_state['email'] = EmailBuilder.BE()

# Don't initialize scrapers at module load time
if 'scrapers' not in st.session_state:
    st.session_state['scrapers'] = {}

# read adverts cache once at launch
if 'vertical_adverts_df' not in st.session_state:
    vert_cache_path = os.path.join(os.getcwd(), "vertical_adverts_cache.csv")
    try:
        df = pd.read_csv(vert_cache_path).astype(str)
        df.dropna(inplace=True, how='all')
    except Exception:
        df = pd.DataFrame([], columns=Advert.__annotations__.keys(), dtype=str)
    st.session_state['vertical_adverts_df'] = df

if 'horizontal_adverts_df' not in st.session_state:
    horiz_cache_path = os.path.join(os.getcwd(), "horizontal_adverts_cache.csv")
    try:
        df = pd.read_csv(horiz_cache_path).astype(str)
    except Exception:
        df = pd.DataFrame([], columns=Advert.__annotations__.keys(), dtype=str)
    st.session_state['horizontal_adverts_df'] = df

# ---------------------------
# Helper Functions
# ---------------------------

def get_email():
    return st.session_state['email']

def update_email_data(key, value):
    email: Email = st.session_state['email']
    setattr(email.data, key, value)
    st.session_state['email'] = email

async def process_urls(urls, site):
    """Process a list of URLs using the appropriate scraper"""
    stories = []
    
    # Create a scraper with a fresh session for this batch of processing
    if site == 'BE':
        scraper = BEScraper()
    else:
        scraper = JEPScraper()
    
    try:
        stories = await scraper.fetch_and_parse_stories(urls)
    except Exception as e:
        logger.error(f"Error processing URLs: {e}")
    finally:
        # Clean up by closing the session
        await scraper.close()
    
    return stories

def _normalized(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    # Ensure same column order/types and no NaNs for stable equality
    if df is None:
        df = pd.DataFrame([], columns=cols, dtype=str)
    if len(df) == 0:
        df = pd.DataFrame([], columns=cols, dtype=str)
    df = df.astype(str).reindex(columns=cols, fill_value="")
    return df.fillna("")

def _csv_equals_df(path: str, df: pd.DataFrame, cols: list[str]) -> bool:
    try:
        on_disk = pd.read_csv(path).astype(str)
    except Exception:
        # File missing or unreadable => treat as different
        return False
    on_disk = _normalized(on_disk, cols)
    current = _normalized(df, cols)
    return on_disk.equals(current)

def save_df_if_changed(path: str, df: pd.DataFrame, cols: list[str]) -> bool:
    """Write CSV only if content differs. Uses atomic replace."""
    df_norm = _normalized(df, cols)
    # If same as on-disk, bail out early
    if os.path.exists(path) and _csv_equals_df(path, df_norm, cols):
        return False
    # Atomic write: write to temp then replace
    tmp = path + ".tmp"
    df_norm.to_csv(tmp, index=False)
    os.replace(tmp, path)
    return True


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
# Main Page Layout
# ---------------------------
st.title(TITLE)

# Input boxes for email parameters
num_stories = st.number_input("Number of News Stories", min_value=1, max_value=20, value=7, step=1)
num_business_stories = st.number_input("Number of Business Stories", min_value=1, max_value=20, value=1, step=1)
num_sports_stories = st.number_input("Number of Sports Stories", min_value=1, max_value=20, value=1, step=1)
num_community_stories = st.number_input("Number of Community Stories", min_value=1, max_value=20, value=1, step=1)
num_podcast_stories = st.number_input("Number of Podcast Stories", min_value=1, max_value=20, value=1, step=1)

# Top image parameters
top_image_url = st.text_input("Top Image URL")
top_image_title = st.text_input("Top Image Title", key="top_image_title")
top_image_author = st.text_input("Top Image Author", key="top_image_author")
top_image_link = st.text_input("Top Image Link (Leave Blank if None)", key="top_image_link")

# Vertical Adverts
st.title("Vertical Adverts")
vertical_adverts_df = st.data_editor(
    st.session_state['vertical_adverts_df'],
    key="vertical_adverts",
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
)

# Horizontal Adverts
st.title("Horizontal Adverts")
horizontal_adverts_df = st.data_editor(
    st.session_state['horizontal_adverts_df'],
    key="horizontal_adverts",
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
)

# ---------------------------
# Ad persistence logic
# ---------------------------
vert_cache_path = os.path.join(os.getcwd(), "vertical_adverts_cache.csv")
horiz_cache_path = os.path.join(os.getcwd(), "horizontal_adverts_cache.csv")
advert_cols = list(Advert.__annotations__.keys())

save_df_if_changed(vert_cache_path, vertical_adverts_df, advert_cols)
save_df_if_changed(horiz_cache_path, horizontal_adverts_df, advert_cols)

# deaths start/end
deaths_start = st.date_input("Deaths Start Date")
deaths_end = st.date_input("Deaths End Date")

# ---------------------------
# Fetch Stories Button
# ---------------------------
st.info("""
    **Note:**
    - If no scraped stories are needed, just leave number to 0.
    - Fetch stories must still be clicked to render connect cover.
""")
if st.button("Fetch Stories"):
    if PROD:
        logger.debug(f'Killing all chrome processes')
        subprocess.run(['killall', 'chrome'])
    with st.spinner("Fetching Stories..."):
        get_email().get_data(
            n_news=num_stories,
            n_business=num_business_stories,
            n_sports=num_sports_stories,
            n_community=num_community_stories,
            n_podcast=num_podcast_stories,
            deaths_start=deaths_start,
            deaths_end=deaths_end)
    st.success("Stories fetched successfully!")

# ---------------------------
# Manual URL Input Section
# ---------------------------
st.title("Add Stories Manually")

# Select which data editor to add to
story_type = st.selectbox("Add to", ["news_stories", "business_stories", "sport_stories", "community_stories", "podcast_stories"], key="manual_url_type")
site = st.selectbox("Site", NEWS_SITES, key="manual_url_site")

# Text area for URLs
manual_urls = st.text_area("Enter URLs (one per line)", key="manual_urls")

# Process manual URLs
if st.button("Process URLs"):
    if manual_urls:
        urls = [url.strip() for url in manual_urls.split("\n") if url.strip()]
        if urls:
            with st.spinner(f"Processing {len(urls)} URLs..."):
                # run async function in sync context
                stories: list[NewsStory] = asyncio.run(process_urls(urls, site))
                if stories:
                    # Get current stories and add new ones
                    current_stories = []
                    for story in get_email().data.get(story_type, []):
                        if isinstance(story, NewsStory):
                            current_stories.append(story)
                        elif isinstance(story, dict):
                            current_stories.append(NewsStory(**story))
                    current_stories.extend(stories)
                    update_email_data(story_type, current_stories)
                    st.success(f"Added {len(stories)} stories to {story_type}")
                    st.rerun()  # Refresh to show updated data editors
                else:
                    st.error("No stories were successfully processed")
        else:
            st.warning("No valid URLs provided")

# Instructions
st.info(
    """
    **Story Ordering Instructions:**
    - Stories are displayed in ascending order based on the 'order' column (1,2,3,...).
    - You can reorder stories by changing the numbers in the 'order' column.
    - Delete stories by selecting and deleting rows.
    """
)

# ---------------------------
# Data Editing
# ---------------------------

def render_data_editor(key):
    try:
        # make dataframe from stories
        df = pd.DataFrame(get_email().data[key], columns=NewsStory.__annotations__.keys())
        # reorder such that order is first column
        columns = ['order'] + [col for col in list(NewsStory.__annotations__.keys()) if col != 'order']
        df = df[columns]
        edited_df = st.data_editor(df, key=key, num_rows="dynamic", use_container_width=True, hide_index=True)
        
        # Save changes back to session state
        if not edited_df.equals(df):
            news_stories = [NewsStory(**row) for row in edited_df.to_dict(orient='records')]
            update_email_data(key, news_stories)
            st.rerun()
        
        return edited_df
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
    
def render_deaths_editor():
    df = pd.DataFrame(get_email().data['family_notices'], columns=FamilyNotice.__annotations__.keys())
    edited_df = st.data_editor(df, key='family_notices', num_rows='dynamic', use_container_width=True, hide_index=True)
    if not edited_df.equals(df):
        family_notices = [FamilyNotice(**row) for row in edited_df.to_dict(orient='records')]
        update_email_data('family_notices', family_notices)
        st.rerun()
    return edited_df

news_stories_df = render_data_editor("news_stories")
business_stories_df = render_data_editor("business_stories")
sport_stories_df = render_data_editor("sport_stories")
community_stories_df = render_data_editor("community_stories")
podcast_stories_df = render_data_editor("podcast_stories")
family_notices_df = render_deaths_editor()

# ---------------------------
# Render Email
# ---------------------------
if st.button("Render Email"):
    rendered_email = Email()
    rendered_email.data['news_stories'] = sorted(news_stories_df.to_dict(orient='records'), key=lambda x: x['order'])
    rendered_email.data['business_stories'] = sorted(business_stories_df.to_dict(orient='records'), key=lambda x: x['order'])
    rendered_email.data['sport_stories'] = sorted(sport_stories_df.to_dict(orient='records'), key=lambda x: x['order'])
    rendered_email.data['community_stories'] = sorted(community_stories_df.to_dict(orient='records'), key=lambda x: x['order'])
    rendered_email.data['podcast_stories'] = sorted(podcast_stories_df.to_dict(orient='records'), key=lambda x: x['order'])
    rendered_email.data['top_image_url'] = top_image_url
    rendered_email.data['top_image_title'] = top_image_title
    rendered_email.data['top_image_author'] = top_image_author
    rendered_email.data['top_image_link'] = top_image_link if top_image_link else None
    rendered_email.data['vertical_adverts'] = vertical_adverts_df.to_dict(orient='records')
    rendered_email.data['horizontal_adverts'] = horizontal_adverts_df.to_dict(orient='records')
    rendered_email.data['weather'] = get_email().data['weather']
    rendered_email.data['family_notices'] = get_email().data['family_notices']
    rendered_email.data['connect_cover_image'] = get_email().data['connect_cover_image']
    print(rendered_email.data['family_notices'])

    rendered_html = rendered_email.render()
    html(rendered_html, height=800, scrolling=True)
    if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
        st.success("Email saved successfully")