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
    sport_stories: list[NewsStory] = field(default_factory=list)
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

def update_horizontal_adverts():
    """Callback function to update horizontal adverts when data editor changes"""
    if "horizontal_adverts" in st.session_state:
        st.session_state[EMAIL_DATA_KEY].horizontal_adverts = df_to_adverts(st.session_state["horizontal_adverts"])

def update_vertical_adverts():
    """Callback function to update vertical adverts when data editor changes"""
    if "vertical_adverts" in st.session_state:
        st.session_state[EMAIL_DATA_KEY].vertical_adverts = vertical_df_to_adverts(st.session_state["vertical_adverts"])

def update_family_notices():
    """Callback function to update family notices when data editor changes"""
    # Don't use the callback parameter, instead sync after the data editor
    pass

def vertical_adverts_to_dataframe(adverts: list[Advert]) -> pd.DataFrame:
    # Old-style structure for vertical adverts (dynamic rows)
    columns = ['order', 'url', 'image_url']
    
    if len(adverts) == 0:
        df = pd.DataFrame(columns=columns)
        df = df.astype({'order': 'Int64', 'url': 'str', 'image_url': 'str'})
        return df
    
    data = []
    for a in adverts:
        data.append({
            'order': a.order if a.order is not None else 0,
            "url": a.url,
            "image_url": a.image_url
        })
    df = pd.DataFrame(data)
    if len(df) > 0 and 'order' in df.columns:
        df['order'] = df['order'].fillna(0).astype('Int64')
        df = df.sort_values('order').reset_index(drop=True)
    return df

def vertical_df_to_adverts(df: pd.DataFrame) -> list[Advert]:
    # Old-style processing for vertical adverts
    adverts = []
    if len(df) == 0:
        return adverts
    
    df = df.copy()
    if 'order' not in df.columns:
        df['order'] = 0
    df['order'] = df['order'].fillna(0)
    
    for _, row in df.sort_values('order').iterrows():
        # Skip rows where url or image_url is NaN/empty
        if pd.isna(row['url']) or pd.isna(row['image_url']) or row['url'] == '' or row['image_url'] == '':
            continue
            
        adverts.append(Advert(
            url=str(row['url']),
            image_url=str(row['image_url']),
            order=int(row.get('order', 0))
        ))
    return adverts

def adverts_to_dataframe(adverts: list[Advert]) -> pd.DataFrame:
    # Define the 7 horizontal advert positions and their descriptions to match the template
    position_descriptions = [
        "After Weather",
        "After Headline Story", 
        "After News Stories",
        "After Business Stories",
        "After Sports Stories", 
        "After Community Stories",
        "After Podcast Stories"
    ]
    
    # Create base structure with all positions
    data = []
    for i, description in enumerate(position_descriptions):
        # Try to find existing advert for this position
        advert_for_position = None
        if i < len(adverts):
            advert_for_position = adverts[i]
        
        data.append({
            'position': f"{i+1}. {description}",
            'url': advert_for_position.url if advert_for_position else "",
            'image_url': advert_for_position.image_url if advert_for_position else "",
            'order': i + 1  # Position order
        })
    
    df = pd.DataFrame(data)
    return df

def df_to_adverts(df: pd.DataFrame) -> list[Advert]:
    adverts = []
    if len(df) == 0:
        return adverts
    
    # Process each row in order (should be 7 rows for the 7 positions)
    for _, row in df.iterrows():
        # Create advert even if empty - empty ones won't render in template
        url = str(row.get('url', '')) if not pd.isna(row.get('url', '')) else ''
        image_url = str(row.get('image_url', '')) if not pd.isna(row.get('image_url', '')) else ''
        order = int(row.get('order', len(adverts) + 1))
        
        adverts.append(Advert(
            url=url,
            image_url=image_url,
            order=order
        ))
    
    # Ensure we always have exactly 7 adverts (pad if needed)
    while len(adverts) < 7:
        adverts.append(Advert(url="", image_url="", order=len(adverts) + 1))
    
    return adverts[:7]  # Limit to 7

def family_notices_to_dataframe(notices: list[FamilyNotice]) -> pd.DataFrame:
    """Convert family notices to editable dataframe"""
    if not notices:
        return pd.DataFrame(columns=['name', 'url', 'funeral_director', 'additional_text'])
    
    data = []
    for notice in notices:
        data.append({
            'name': notice.name,
            'url': notice.url,
            'funeral_director': notice.funeral_director,
            'additional_text': notice.additional_text
        })
    
    return pd.DataFrame(data)

def df_to_family_notices(df: pd.DataFrame) -> list[FamilyNotice]:
    """Convert dataframe back to family notices"""
    notices = []
    
    # Handle case where df might not be a DataFrame
    if not isinstance(df, pd.DataFrame):
        return notices
        
    if len(df) == 0:
        return notices
    
    for _, row in df.iterrows():
        # Skip rows where name is empty/NaN
        if pd.isna(row.get('name', '')) or str(row.get('name', '')).strip() == '':
            continue
        
        # Helper function to safely convert values to strings, handling None/NaN
        def safe_str(value):
            if pd.isna(value) or value is None:
                return ''
            return str(value).strip()
            
        notices.append(FamilyNotice(
            name=safe_str(row.get('name', '')),
            url=safe_str(row.get('url', '')),
            funeral_director=safe_str(row.get('funeral_director', '')),
            additional_text=safe_str(row.get('additional_text', ''))
        ))
    
    return notices

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
        "sport_stories": news_scraper.get_n_stories_for_region("jsy_sport", num_sports),
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

# ---------------------------
# Left column data input
# ---------------------------
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

    # Initialize dataframe keys in session state if they don't exist
    if "vertical_adverts_df" not in st.session_state:
        st.session_state["vertical_adverts_df"] = vertical_adverts_to_dataframe(st.session_state[EMAIL_DATA_KEY].vertical_adverts)
    if "horizontal_adverts_df" not in st.session_state:
        st.session_state["horizontal_adverts_df"] = adverts_to_dataframe(st.session_state[EMAIL_DATA_KEY].horizontal_adverts)
    if "family_notices_df" not in st.session_state:
        st.session_state["family_notices_df"] = family_notices_to_dataframe(st.session_state[EMAIL_DATA_KEY].family_notices)
    
    # Ensure dataframes always have the correct columns only if they're completely empty or malformed
    # Vertical adverts keep the old structure (dynamic rows)
    vertical_required_columns = ['order', 'url', 'image_url']
    if (st.session_state["vertical_adverts_df"].empty or 
        not all(col in st.session_state["vertical_adverts_df"].columns for col in vertical_required_columns)):
        # Create old-style vertical adverts dataframe
        columns = ['order', 'url', 'image_url']
        df = pd.DataFrame(columns=columns)
        df = df.astype({'order': 'Int64', 'url': 'str', 'image_url': 'str'})
        st.session_state["vertical_adverts_df"] = df
    
    # Horizontal adverts use new structure (fixed 7 rows with position descriptions)
    horizontal_required_columns = ['position', 'url', 'image_url', 'order']
    if (st.session_state["horizontal_adverts_df"].empty or 
        not all(col in st.session_state["horizontal_adverts_df"].columns for col in horizontal_required_columns)):
        st.session_state["horizontal_adverts_df"] = adverts_to_dataframe([])

    # advert tables
    st.subheader("Vertical Adverts")
    vertical_adverts_df = st.data_editor(
        st.session_state["vertical_adverts_df"],
        key="vertical_adverts",
        num_rows="dynamic",
        width='stretch',
        hide_index=True,
        on_change=update_vertical_adverts
    )
    
    st.subheader("Horizontal Adverts (Leave URL and Image URL blank to skip a position)")
    horizontal_adverts_df = st.data_editor(
        st.session_state["horizontal_adverts_df"],
        key="horizontal_adverts",
        num_rows="fixed",  # Fixed rows, no adding/deleting
        width='stretch',
        hide_index=True,
        on_change=update_horizontal_adverts,
        column_config={
            "position": st.column_config.TextColumn(
                "Position",
                help="Where this advert will appear in the email",
                disabled=True,  # Make read-only
                width="large"
            ),
            "url": st.column_config.TextColumn(
                "URL",
                help="Link when advert is clicked (leave blank to skip this position)",
                width="medium"
            ),
            "image_url": st.column_config.TextColumn(
                "Image URL", 
                help="Image to display (leave blank to skip this position)",
                width="medium"
            ),
            "order": None  # Hide the order column
        }
    )

    subcol1, subcol2, subcol3 = st.columns(3)
    with subcol1:
        if st.button("Save Adverts"):
            vertical_adverts_df.to_csv(VA_CACHE_PATH, index=False)
            horizontal_adverts_df.to_csv(HA_CACHE_PATH, index=False)
            st.success("Saved Adverts Cache")

    with subcol2:
        if st.button("Load Adverts"):
            if os.path.exists(HA_CACHE_PATH):
                print("FOUND HA CACHE")
                try:
                    hdf = pd.read_csv(HA_CACHE_PATH)
                    # Check if it's the new format (has 'position' column) or old format
                    if 'position' in hdf.columns:
                        st.session_state[EMAIL_DATA_KEY].horizontal_adverts = df_to_adverts(hdf)
                        st.session_state["horizontal_adverts_df"] = hdf.copy()
                    else:
                        # Old format - convert to new format
                        old_adverts = vertical_df_to_adverts(hdf)  # Use old parser
                        st.session_state[EMAIL_DATA_KEY].horizontal_adverts = old_adverts
                        st.session_state["horizontal_adverts_df"] = adverts_to_dataframe(old_adverts)
                except Exception as e:
                    st.error(f"Couldn't load horizontal adverts cache: {e}")
            else:
                st.error("No horizontal adverts cache found")
            if os.path.exists(VA_CACHE_PATH):
                print("FOUND VA CACHE")
                try:
                    vdf = pd.read_csv(VA_CACHE_PATH)
                    st.session_state[EMAIL_DATA_KEY].vertical_adverts = vertical_df_to_adverts(vdf)
                    st.session_state["vertical_adverts_df"] = vdf.copy()
                except Exception as e:
                    st.error(f"Couldn't load vertical adverts cache: {e}")
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
            
            # Preserve existing adverts data
            email_data.vertical_adverts = st.session_state[EMAIL_DATA_KEY].vertical_adverts
            email_data.horizontal_adverts = st.session_state[EMAIL_DATA_KEY].horizontal_adverts
            
            st.session_state[EMAIL_DATA_KEY] = email_data
            # Update family notices dataframe with fetched data
            st.session_state["family_notices_df"] = family_notices_to_dataframe(email_data.family_notices)
            # Don't reset advert dataframes - keep the existing ones
            st.rerun()

    # edit story dataframes
    st.markdown("#### News Stories")
    news_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].news_stories), key="news_stories", hide_index=True, num_rows='dynamic')
    
    st.markdown("#### Business Stories")
    business_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].business_stories), key="business_stories", hide_index=True, num_rows='dynamic')
    
    st.markdown("#### Sports Stories")
    sports_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].sport_stories), key="sports_stories", hide_index=True, num_rows='dynamic')
    
    st.markdown("#### Community Stories")
    community_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].community_stories), key="community_stories", hide_index=True, num_rows='dynamic')
    
    st.markdown("#### Podcast Stories")
    podcast_df = st.data_editor(stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].podcast_stories), key="podcast_stories", hide_index=True, num_rows='dynamic')

    st.markdown("#### Family Notices")
    family_notices_df = st.data_editor(
        st.session_state["family_notices_df"],
        key="family_notices",
        num_rows="dynamic",
        width='stretch',
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn(
                "Name",
                help="Full name of the deceased",
                width="medium"
            ),
            "url": st.column_config.TextColumn(
                "URL",
                help="Link to the full family notice",
                width="medium"
            ),
            "funeral_director": st.column_config.TextColumn(
                "Funeral Director",
                help="Name of the funeral director handling arrangements",
                width="medium"
            ),
            "additional_text": st.column_config.TextColumn(
                "Additional Text",
                help="Any additional text or information",
                width="large"
            )
        }
    )

    # update email data state
    st.session_state[EMAIL_DATA_KEY].news_stories = df_to_stories(news_df)
    st.session_state[EMAIL_DATA_KEY].business_stories = df_to_stories(business_df)
    st.session_state[EMAIL_DATA_KEY].sport_stories = df_to_stories(sports_df)
    st.session_state[EMAIL_DATA_KEY].community_stories = df_to_stories(community_df)
    st.session_state[EMAIL_DATA_KEY].podcast_stories = df_to_stories(podcast_df)
    st.session_state[EMAIL_DATA_KEY].family_notices = df_to_family_notices(family_notices_df)
    st.session_state[EMAIL_DATA_KEY].top_image = TopImage(
        title=top_image_title,
        url = top_image_url,
        author = top_image_author,
        link = top_image_link
    )
    
    # Adverts are now updated via callbacks, no need for manual comparison

    # Manual URL Input Section
    st.title("Add Stories Manually")
    story_type = st.selectbox("Add to", ["news_stories", "business_stories", "sport_stories", "community_stories", "podcast_stories"], key="manual_url_type")
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

# ---------------------------
# Right column html rendering
# ---------------------------
with col2:

    if len(st.session_state[EMAIL_DATA_KEY].news_stories) > 0:
        rendered_html = EmailBuilder.BE().render(st.session_state[EMAIL_DATA_KEY])
        html(rendered_html, scrolling=True, height=3000)

        if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
            st.success("Email saved successfully")