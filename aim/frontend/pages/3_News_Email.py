import os
import logging

import streamlit as st
import pandas as pd
from streamlit.components.v1 import html

from aim.emailer.base import Email, Advert
from aim.news.models import NewsStory

logger = logging.getLogger(__name__)

TITLE = "News Email"
NEWS_SITES = ["BE", "JEP"]

# ---------------------------
# Initialize Session State
# ---------------------------
if "email_vars" not in st.session_state:
    st.session_state["email_vars"] = {
        "weather": "",
        "news_stories": [],
        "business_stories": [],
        "sport_stories": [],
        "top_image_url": "",
        "top_image_title": "",
        "top_image_author": "",
        "vertical_adverts": [],
    }

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# We also store the DataFrames separately in session_state,
# so that user edits remain across reruns (unless we explicitly overwrite them).
if "news_df" not in st.session_state:
    st.session_state["news_df"] = pd.DataFrame()
if "business_df" not in st.session_state:
    st.session_state["business_df"] = pd.DataFrame()
if "sports_df" not in st.session_state:
    st.session_state["sports_df"] = pd.DataFrame()

# ---------------------------
# Load Secrets
# ---------------------------
try:
    try:
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        STREAMLIT_USER = os.getenv("STREAMLIT_USER")
        STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")
        logger.debug("Secrets loaded from .env file")
    except Exception:
        STREAMLIT_USER = st.secrets["STREAMLIT_USER"]
        STREAMLIT_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]
        logger.debug("Secrets loaded from Streamlit Secrets")
except Exception as e:
    logger.error("Failed to load secrets")
    logger.error(e)


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

st.session_state["email_vars"]["top_image_url"] = st.text_input("Top Image URL")
st.session_state["email_vars"]["top_image_title"] = st.text_input("Top Image Title")
st.session_state["email_vars"]["top_image_author"] = st.text_input("Top Image Author")

# Vertical Adverts
st.header("Vertical Adverts")
vertical_adverts_df = (
    pd.DataFrame.from_records(
        [advert.__dict__ for advert in st.session_state["email_vars"]["vertical_adverts"]]
    )
    if st.session_state["email_vars"]["vertical_adverts"]
    else pd.DataFrame(columns=["url", "image_url"])
)
edited_adverts_df = st.data_editor(
    vertical_adverts_df,
    key="vertical_banners_editor",
    num_rows="dynamic",
    use_container_width=True,
)

# Update adverts in session state
st.session_state["email_vars"]["vertical_adverts"] = [
    Advert(**row) for row in edited_adverts_df.to_dict("records")
]

# ---------------------------
# Fetch Stories Button
# ---------------------------
if st.button("Fetch Stories"):
    email = Email(template_name="be_template.html")

    with st.spinner("Fetching Stories..."):
        email.get_data(num_stories, num_business_stories, num_sports_stories)
        st.session_state["email_vars"]["news_stories"] = email.news_stories
        st.session_state["email_vars"]["business_stories"] = email.business_stories
        st.session_state["email_vars"]["sport_stories"] = email.sport_stories
        st.session_state["email_vars"]["weather"] = email.weather

        # Build the DataFrames for editing
        news_df = pd.DataFrame(email.news_stories)
        if not news_df.empty and "order" not in news_df.columns:
            news_df.insert(0, "order", range(1, len(news_df) + 1))
        st.session_state["news_df"] = news_df

        business_df = pd.DataFrame(email.business_stories)
        if not business_df.empty and "order" not in business_df.columns:
            business_df.insert(0, "order", range(1, len(business_df) + 1))
        st.session_state["business_df"] = business_df

        sports_df = pd.DataFrame(email.sport_stories)
        if not sports_df.empty and "order" not in sports_df.columns:
            sports_df.insert(0, "order", range(1, len(sports_df) + 1))
        st.session_state["sports_df"] = sports_df

    st.success("Stories fetched successfully!")


st.info(
    """
    **Story Ordering Instructions:**
    - Stories are displayed in ascending order based on the 'order' column (1,2,3,...).
    - You can reorder stories by changing the numbers in the 'order' column.
    - Stories with order=0 will not appear.
    """
)

# ---------------------------
# Data Editing
# ---------------------------
# NEWS
news_df = st.session_state["news_df"]
news_df = st.data_editor(
    news_df,
    key="news_data_editor",
    num_rows="dynamic",
    use_container_width=True,
)
# Save changes back
st.session_state["news_df"] = news_df

# BUSINESS
business_df = st.session_state["business_df"]
business_df = st.data_editor(
    business_df,
    key="business_data_editor",
    num_rows="dynamic",
    use_container_width=True,
)
st.session_state["business_df"] = business_df

# SPORTS
sports_df = st.session_state["sports_df"]
sports_df = st.data_editor(
    sports_df,
    key="sports_data_editor",
    num_rows="dynamic",
    use_container_width=True,
)
st.session_state["sports_df"] = sports_df

# ---------------------------
# Render Email
# ---------------------------
if st.button("Render Email"):
    # Convert DFs back to lists of NewsStory objects, sorted by 'order'
    def to_stories(df: pd.DataFrame) -> list[NewsStory]:
        if df.empty:
            return []
        df_sorted = df.sort_values("order")
        # Keep only the fields that map to NewsStory
        columns = list(NewsStory.__annotations__.keys())
        # Drop any columns not in NewsStory (like 'order')
        df_cleaned = df_sorted[columns].copy()
        return [NewsStory(**row) for _, row in df_cleaned.iterrows()]

    st.session_state["email_vars"]["news_stories"] = to_stories(st.session_state["news_df"])
    st.session_state["email_vars"]["business_stories"] = to_stories(st.session_state["business_df"])
    st.session_state["email_vars"]["sport_stories"] = to_stories(st.session_state["sports_df"])

    # Reuse the same Email object to render
    email = Email(template_name="be_template.html")
    rendered_html = email.render(**st.session_state["email_vars"])

    # Display the rendered HTML in the Streamlit app
    html(rendered_html, height=800, scrolling=True)

    # Provide a download button
    if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
        st.success("Email saved successfully")
