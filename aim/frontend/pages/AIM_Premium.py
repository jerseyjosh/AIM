import streamlit as st
import pandas as pd
import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from streamlit.components.v1 import html

from aim.news.jep_scraper import JEPScraper
from aim.news.models import NewsStory, Foreword, ForewordAuthor
from aim.emailer.base import EmailBuilder

logger = logging.getLogger(__name__)

TITLE = "AIM Premium"
EMAIL_DATA_KEY = "aim_premium_email_data"
LOGGED_IN_KEY = "logged_in"

if LOGGED_IN_KEY not in st.session_state:
    st.session_state[LOGGED_IN_KEY] = False

st.set_page_config(layout="wide")

# ---------------------------
# Load Secrets
# ---------------------------
try:
    # Load secrets here if needed
    pass
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
        # Add authentication logic here
        if username and password:  # Simplified auth for demo
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Please enter username and password")
    st.stop()

# ---------------------------
# Helper Functions
# ---------------------------

@dataclass
class AIMPremiumEmailData:
    title: str = field(default="Your brunch reading")
    news_stories: list[NewsStory] = field(default_factory=list)
    foreword: Foreword = field(default_factory=lambda: Foreword(
        author=ForewordAuthor.Fiona,
        text="",
        title="The best of our journalism"
    ))

if EMAIL_DATA_KEY not in st.session_state:
    st.session_state[EMAIL_DATA_KEY] = AIMPremiumEmailData()

def stories_to_dataframe(stories: list[NewsStory]) -> pd.DataFrame:
    """Convert stories to editable dataframe"""
    if not stories:
        return pd.DataFrame(columns=['order', 'headline', 'url', 'date', 'author'])
    
    data = []
    for s in stories:
        data.append({
            'order': s.order,
            'headline': s.headline,
            'url': s.url,
            'date': s.date,
            'author': s.author
        })
    
    df = pd.DataFrame(data)
    if 'order' in df.columns:
        df = df.sort_values('order')
    return df

def df_to_stories(df: pd.DataFrame) -> list[NewsStory]:
    """Convert dataframe back to stories"""
    stories = []
    if 'order' not in df.columns:
        df['order'] = range(len(df))
    
    for _, row in df.sort_values('order').iterrows():
        # Find the original story to preserve all fields
        original_story = next(
            (s for s in st.session_state[EMAIL_DATA_KEY].news_stories if s.url == row['url']), 
            None
        )
        if original_story:
            # Update order from dataframe
            story = NewsStory(
                headline=original_story.headline,
                text=original_story.text,
                date=original_story.date,
                author=original_story.author,
                url=original_story.url,
                image_url=original_story.image_url,
                order=int(row['order'])
            )
            stories.append(story)
    
    return stories

async def get_email_data(num_stories: int, foreword_author: ForewordAuthor, foreword_text: str, foreword_title: str, cryptic_clue: str, title: str) -> AIMPremiumEmailData:
    """Fetch all data for email asynchronously"""
    scraper = JEPScraper()
    
    try:
        # Get premium stories from JEP
        stories = await scraper.get_n_stories_for_region("jsy_premium", num_stories)
        await scraper.close()
        
        # Create foreword
        foreword = Foreword(
            author=foreword_author,
            text=foreword_text,
            title=foreword_title,
            cryptic_clue=cryptic_clue
        )
        
        return AIMPremiumEmailData(
            title=title,
            news_stories=stories,
            foreword=foreword
        )
    except Exception as e:
        logger.error(f"Error fetching email data: {e}")
        await scraper.close()
        raise e

async def manually_scrape_urls(urls: list[str]):
    """Manually scrape list of urls"""
    scraper = JEPScraper()
    try:
        stories = await scraper.fetch_and_parse_stories(urls)
        await scraper.close()
        return [s for s in stories if s and not isinstance(s, Exception)]
    except Exception as e:
        logger.error(f"Error manually scraping URLs: {e}")
        await scraper.close()
        raise e

# ---------------------------
# Main Page Layout
# ---------------------------
st.title(TITLE)

col1, col2 = st.columns(2)

# ---------------------------
# Left column data input
# ---------------------------
with col1:
    st.header("Email Configuration")
    
    # Email parameters
    title = st.text_input("Email Title", value="Your brunch reading", key="email_title")
    num_stories = st.number_input("Number of Stories", min_value=1, max_value=20, value=5, step=1)
    
    # Foreword configuration
    st.subheader("Foreword Configuration")
    foreword_author = st.selectbox(
        "Foreword Author",
        options=list(ForewordAuthor),
        format_func=lambda x: x.name,
        key="foreword_author"
    )
    
    foreword_title = st.text_input(
        "Foreword Title",
        value="The best of our journalism",
        key="foreword_title"
    )
    
    foreword_text = st.text_area(
        "Foreword Text",
        value="",
        height=150,
        key="foreword_text"
    )
    
    cryptic_clue = st.text_input(
        "Cryptic Crossword Clue",
        value="One glass and he fails to stand up (7)",
        key="cryptic_clue"
    )
    
    # Fetch data button
    if st.button("Fetch Stories", type="primary"):
        with st.spinner("Fetching premium stories..."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                email_data = loop.run_until_complete(
                    get_email_data(num_stories, foreword_author, foreword_text, foreword_title, cryptic_clue, title)
                )
                st.session_state[EMAIL_DATA_KEY] = email_data
                st.success(f"Successfully fetched {len(email_data.news_stories)} stories!")
                st.rerun()
            except Exception as e:
                st.error(f"Error fetching stories: {e}")
            finally:
                loop.close()
    
    # Edit stories dataframe
    st.subheader("Stories")
    if st.session_state[EMAIL_DATA_KEY].news_stories:
        stories_df = st.data_editor(
            stories_to_dataframe(st.session_state[EMAIL_DATA_KEY].news_stories),
            key="stories_editor",
            hide_index=True,
            num_rows='dynamic',
            column_config={
                "order": st.column_config.NumberColumn(
                    "Order",
                    help="Story order in email",
                    min_value=0,
                    max_value=100,
                    step=1,
                    format="%d"
                ),
                "headline": st.column_config.TextColumn(
                    "Headline",
                    help="Story headline",
                    width="large"
                ),
                "url": st.column_config.LinkColumn(
                    "URL",
                    help="Story URL",
                    width="medium"
                ),
                "date": st.column_config.TextColumn(
                    "Date",
                    help="Publication date",
                    width="small"
                ),
                "author": st.column_config.TextColumn(
                    "Author",
                    help="Story author",
                    width="medium"
                )
            }
        )
        
        # Update session state with edited stories
        st.session_state[EMAIL_DATA_KEY].news_stories = df_to_stories(stories_df)
    else:
        st.info("No stories loaded. Click 'Fetch Stories' to load premium content.")
    
    # Update email data with current form values
    st.session_state[EMAIL_DATA_KEY].title = title
    st.session_state[EMAIL_DATA_KEY].foreword = Foreword(
        author=foreword_author,
        text=foreword_text,
        title=foreword_title,
        cryptic_clue=cryptic_clue
    )
    
    # Manual URL Input Section
    st.subheader("Add Stories Manually")
    manual_urls = st.text_area(
        "Story URLs (one per line)",
        height=100,
        placeholder="https://jerseyeveningpost.com/...\nhttps://jerseyeveningpost.com/...",
        key="manual_urls"
    )
    
    if st.button("Add Manual Stories") and manual_urls:
        urls = [url.strip() for url in manual_urls.split('\n') if url.strip()]
        if urls:
            with st.spinner(f"Scraping {len(urls)} stories..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    new_stories = loop.run_until_complete(manually_scrape_urls(urls))
                    
                    # Add new stories to existing ones
                    current_stories = st.session_state[EMAIL_DATA_KEY].news_stories
                    max_order = max([s.order for s in current_stories], default=0)
                    
                    for i, story in enumerate(new_stories):
                        story_with_order = NewsStory(
                            headline=story.headline,
                            text=story.text,
                            date=story.date,
                            author=story.author,
                            url=story.url,
                            image_url=story.image_url,
                            order=max_order + i + 1
                        )
                        current_stories.append(story_with_order)
                    
                    st.session_state[EMAIL_DATA_KEY].news_stories = current_stories
                    st.success(f"Added {len(new_stories)} stories!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error scraping URLs: {e}")
                finally:
                    loop.close()

# ---------------------------
# Right column html rendering
# ---------------------------
with col2:
    
    # Always try to render email if we have data
    email_data = st.session_state[EMAIL_DATA_KEY]
    
    # Generate email HTML and display it (matching BE_Email.py pattern)
    rendered_html = EmailBuilder.AIMPremium().render(email_data)
    html(rendered_html, scrolling=True, height=2000)

    if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
        st.success("Email saved successfully")

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown("**AIM Premium Email Builder** - Create beautiful premium newsletters")
