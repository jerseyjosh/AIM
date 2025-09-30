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
    
    # Validate input is a DataFrame
    if not isinstance(df, pd.DataFrame):
        logger.warning(f"df_to_stories received {type(df)} instead of DataFrame")
        return stories
        
    if len(df) == 0:
        return stories
        
    df = df.copy()
    if 'order' not in df.columns:
        df['order'] = 0
    
    # Ensure all required columns exist
    required_columns = ['headline', 'date', 'author', 'text', 'url', 'image_url']
    for col in required_columns:
        if col not in df.columns:
            logger.warning(f"Missing column '{col}' in DataFrame, adding with empty values")
            df[col] = ""
    
    for _, row in df.sort_values('order').iterrows():
        stories.append(NewsStory(
            order=row.get("order", 0),
            headline=row.get("headline", ""),
            date=row.get("date", ""),
            author=row.get("author", ""),
            text=row.get("text", ""),
            url=row.get("url", ""),
            image_url=row.get("image_url", ""),
        ))
    return stories

def update_horizontal_adverts():
    """Callback function to update horizontal adverts when data editor changes"""
    if "horizontal_adverts" in st.session_state:
        data = st.session_state["horizontal_adverts"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].horizontal_adverts = df_to_adverts(data)
            st.session_state["horizontal_adverts_df"] = data.copy()

def update_vertical_adverts():
    """Callback function to update vertical adverts when data editor changes"""
    if "vertical_adverts" in st.session_state:
        data = st.session_state["vertical_adverts"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].vertical_adverts = vertical_df_to_adverts(data)
            st.session_state["vertical_adverts_df"] = data.copy()

def update_family_notices():
    """Callback function to update family notices when data editor changes"""
    # Don't use the callback parameter, instead sync after the data editor
    pass

def update_news_stories():
    """Callback function to update news stories when data editor changes"""
    if "news_stories" in st.session_state:
        data = st.session_state["news_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].news_stories = df_to_stories(data)
            st.session_state["news_stories_df"] = data.copy()

def update_business_stories():
    """Callback function to update business stories when data editor changes"""
    if "business_stories" in st.session_state:
        data = st.session_state["business_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].business_stories = df_to_stories(data)
            st.session_state["business_stories_df"] = data.copy()

def update_sports_stories():
    """Callback function to update sports stories when data editor changes"""
    if "sports_stories" in st.session_state:
        data = st.session_state["sports_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].sport_stories = df_to_stories(data)
            st.session_state["sports_stories_df"] = data.copy()

def update_community_stories():
    """Callback function to update community stories when data editor changes"""
    if "community_stories" in st.session_state:
        data = st.session_state["community_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].community_stories = df_to_stories(data)
            st.session_state["community_stories_df"] = data.copy()

def update_podcast_stories():
    """Callback function to update podcast stories when data editor changes"""
    if "podcast_stories" in st.session_state:
        data = st.session_state["podcast_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].podcast_stories = df_to_stories(data)
            st.session_state["podcast_stories_df"] = data.copy()

def update_business_stories():
    """Callback function to update business stories when data editor changes"""
    if "business_stories" in st.session_state:
        data = st.session_state["business_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].business_stories = df_to_stories(data)
            st.session_state["business_stories_df"] = data.copy()

def update_sports_stories():
    """Callback function to update sports stories when data editor changes"""
    if "sports_stories" in st.session_state:
        data = st.session_state["sports_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].sport_stories = df_to_stories(data)
            st.session_state["sports_stories_df"] = data.copy()

def update_community_stories():
    """Callback function to update community stories when data editor changes"""
    if "community_stories" in st.session_state:
        data = st.session_state["community_stories"]
        if isinstance(data, pd.DataFrame):
            st.session_state[EMAIL_DATA_KEY].community_stories = df_to_stories(data)
            st.session_state["community_stories_df"] = data.copy()

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
    
    # Validate input is a DataFrame
    if not isinstance(df, pd.DataFrame):
        logger.warning(f"vertical_df_to_adverts received {type(df)} instead of DataFrame")
        return adverts
        
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
    # Define the 8 horizontal advert positions and their descriptions to match the template
    # Order: weather, headline, news, sports, community, business, podcast, family notices
    position_descriptions = [
        "After Weather",
        "After Headline Story", 
        "After News Stories",
        "After Sports Stories",
        "After Community Stories", 
        "After Business Stories",
        "After Podcast Stories",
        "After Family Notices"
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
    
    # Validate input is a DataFrame
    if not isinstance(df, pd.DataFrame):
        logger.warning(f"df_to_adverts received {type(df)} instead of DataFrame")
        return adverts
        
    if len(df) == 0:
        return adverts
    
    # Process each row in order (should be 8 rows for the 8 positions)
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
    
    # Ensure we always have exactly 8 adverts (pad if needed)
    while len(adverts) < 8:
        adverts.append(Advert(url="", image_url="", order=len(adverts) + 1))
    
    return adverts[:8]  # Limit to 8

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
        logger.warning(f"df_to_family_notices received {type(df)} instead of DataFrame")
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
    
    # Initialize story dataframes for persistent state
    if "news_stories_df" not in st.session_state:
        st.session_state["news_stories_df"] = stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].news_stories)
    if "business_stories_df" not in st.session_state:
        st.session_state["business_stories_df"] = stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].business_stories)
    if "sports_stories_df" not in st.session_state:
        st.session_state["sports_stories_df"] = stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].sport_stories)
    if "community_stories_df" not in st.session_state:
        st.session_state["community_stories_df"] = stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].community_stories)
    if "podcast_stories_df" not in st.session_state:
        st.session_state["podcast_stories_df"] = stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].podcast_stories)
    
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
    
    st.subheader("Horizontal Adverts")
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
    
    # Explicit synchronization: Update session state from current dataframe values
    # This ensures the HTML rendering reflects any changes made in the data editors
    
    # Handle horizontal adverts (convert dict to DataFrame if needed)
    if isinstance(horizontal_adverts_df, pd.DataFrame):
        st.session_state[EMAIL_DATA_KEY].horizontal_adverts = df_to_adverts(horizontal_adverts_df)
    elif isinstance(horizontal_adverts_df, dict):
        try:
            df = pd.DataFrame(horizontal_adverts_df)
            st.session_state[EMAIL_DATA_KEY].horizontal_adverts = df_to_adverts(df)
            logger.debug("Converted horizontal_adverts_df dict to DataFrame for sync")
        except Exception as e:
            logger.error(f"Failed to convert horizontal_adverts_df dict to DataFrame: {e}")
    
    # Handle vertical adverts (convert dict to DataFrame if needed)
    if isinstance(vertical_adverts_df, pd.DataFrame):
        st.session_state[EMAIL_DATA_KEY].vertical_adverts = vertical_df_to_adverts(vertical_adverts_df)
    elif isinstance(vertical_adverts_df, dict):
        try:
            df = pd.DataFrame(vertical_adverts_df)
            st.session_state[EMAIL_DATA_KEY].vertical_adverts = vertical_df_to_adverts(df)
            logger.debug("Converted vertical_adverts_df dict to DataFrame for sync")
        except Exception as e:
            logger.error(f"Failed to convert vertical_adverts_df dict to DataFrame: {e}")

    subcol1, subcol2, subcol3 = st.columns(3)
    with subcol1:
        if st.button("Save Adverts"):
            try:
                # Validate that we have DataFrames before saving
                if not isinstance(vertical_adverts_df, pd.DataFrame):
                    st.error(f"Cannot save vertical adverts: not a DataFrame (type: {type(vertical_adverts_df)})")
                elif not isinstance(horizontal_adverts_df, pd.DataFrame):
                    st.error(f"Cannot save horizontal adverts: not a DataFrame (type: {type(horizontal_adverts_df)})")
                else:
                    vertical_adverts_df.to_csv(VA_CACHE_PATH, index=False)
                    horizontal_adverts_df.to_csv(HA_CACHE_PATH, index=False)
                    st.success("Saved Adverts Cache")
            except Exception as e:
                st.error(f"Failed to save adverts cache: {e}")
                logger.error(f"Failed to save adverts cache: {e}")

    with subcol2:
        if st.button("Load Adverts"):
            if os.path.exists(HA_CACHE_PATH):
                print("FOUND HA CACHE")
                try:
                    hdf = pd.read_csv(HA_CACHE_PATH)
                    # Validate that we loaded a DataFrame
                    if not isinstance(hdf, pd.DataFrame):
                        st.error(f"Horizontal adverts cache loaded as {type(hdf)}, expected DataFrame")
                    else:
                        # Check if it's the new format (has 'position' column) or old format
                        if 'position' in hdf.columns:
                            # New format: ensure we have all 7 positions with correct descriptions
                            loaded_adverts = df_to_adverts(hdf)
                            # Create a properly formatted dataframe with all positions
                            st.session_state["horizontal_adverts_df"] = adverts_to_dataframe(loaded_adverts)
                            st.session_state[EMAIL_DATA_KEY].horizontal_adverts = loaded_adverts
                        else:
                            # Old format - convert to new format
                            old_adverts = vertical_df_to_adverts(hdf)  # Use old parser
                            st.session_state[EMAIL_DATA_KEY].horizontal_adverts = old_adverts
                            st.session_state["horizontal_adverts_df"] = adverts_to_dataframe(old_adverts)
                except Exception as e:
                    st.error(f"Couldn't load horizontal adverts cache: {e}")
                    logger.error(f"Failed to load horizontal adverts cache: {e}")
            else:
                st.error("No horizontal adverts cache found")
            if os.path.exists(VA_CACHE_PATH):
                print("FOUND VA CACHE")
                try:
                    vdf = pd.read_csv(VA_CACHE_PATH)
                    # Validate that we loaded a DataFrame
                    if not isinstance(vdf, pd.DataFrame):
                        st.error(f"Vertical adverts cache loaded as {type(vdf)}, expected DataFrame")
                    else:
                        st.session_state[EMAIL_DATA_KEY].vertical_adverts = vertical_df_to_adverts(vdf)
                        st.session_state["vertical_adverts_df"] = vdf.copy()
                except Exception as e:
                    st.error(f"Couldn't load vertical adverts cache: {e}")
                    logger.error(f"Failed to load vertical adverts cache: {e}")
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
            # Update all dataframes with fetched data
            st.session_state["family_notices_df"] = family_notices_to_dataframe(email_data.family_notices)
            st.session_state["news_stories_df"] = stories_to_dataframe(email_data.news_stories)
            st.session_state["business_stories_df"] = stories_to_dataframe(email_data.business_stories)
            st.session_state["sports_stories_df"] = stories_to_dataframe(email_data.sport_stories)
            st.session_state["community_stories_df"] = stories_to_dataframe(email_data.community_stories)
            st.session_state["podcast_stories_df"] = stories_to_dataframe(email_data.podcast_stories)
            # Don't reset advert dataframes - keep the existing ones
            st.rerun()

    # edit story dataframes
    st.markdown("#### News Stories")
    news_df = st.data_editor(st.session_state["news_stories_df"], key="news_stories", hide_index=True, num_rows='dynamic', on_change=update_news_stories)
    
    st.markdown("#### Business Stories")
    business_df = st.data_editor(st.session_state["business_stories_df"], key="business_stories", hide_index=True, num_rows='dynamic', on_change=update_business_stories)
    
    st.markdown("#### Sports Stories")
    sports_df = st.data_editor(st.session_state["sports_stories_df"], key="sports_stories", hide_index=True, num_rows='dynamic', on_change=update_sports_stories)
    
    st.markdown("#### Community Stories")
    community_df = st.data_editor(st.session_state["community_stories_df"], key="community_stories", hide_index=True, num_rows='dynamic', on_change=update_community_stories)
    
    st.markdown("#### Podcast Stories")
    podcast_df = st.data_editor(st.session_state["podcast_stories_df"], key="podcast_stories", hide_index=True, num_rows='dynamic', on_change=update_podcast_stories)

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
    
    # Explicit synchronization for story dataframes
    # This ensures story changes are reflected immediately in the email data
    story_dfs = [
        ("news_stories", news_df),
        ("business_stories", business_df), 
        ("sport_stories", sports_df),
        ("community_stories", community_df),
        ("podcast_stories", podcast_df)
    ]
    
    for attr_name, df in story_dfs:
        if isinstance(df, pd.DataFrame):
            setattr(st.session_state[EMAIL_DATA_KEY], attr_name, df_to_stories(df))

    # update email data state (stories handled by explicit sync above)
    st.session_state[EMAIL_DATA_KEY].family_notices = df_to_family_notices(family_notices_df)
    
    # Update persistent dataframes to maintain state
    st.session_state["news_stories_df"] = news_df.copy() if isinstance(news_df, pd.DataFrame) else news_df
    st.session_state["business_stories_df"] = business_df.copy() if isinstance(business_df, pd.DataFrame) else business_df
    st.session_state["sports_stories_df"] = sports_df.copy() if isinstance(sports_df, pd.DataFrame) else sports_df
    st.session_state["community_stories_df"] = community_df.copy() if isinstance(community_df, pd.DataFrame) else community_df
    st.session_state["podcast_stories_df"] = podcast_df.copy() if isinstance(podcast_df, pd.DataFrame) else podcast_df
    
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
            combined_stories = current_stories + new_stories
            # update email data
            setattr(st.session_state[EMAIL_DATA_KEY], story_type, combined_stories)
            
            # Also update the persistent dataframes that the data editors use
            dataframe_key = f"{story_type}_df"
            if story_type == "sport_stories":
                dataframe_key = "sports_stories_df"  # Handle the naming inconsistency
            
            # Update the persistent dataframe
            st.session_state[dataframe_key] = stories_to_dataframe(combined_stories)
            
            st.success(f"Added {len(new_stories)} new stories to {story_type}")
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