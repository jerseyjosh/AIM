import os
import logging

import streamlit as st
import pandas as pd
from streamlit.components.v1 import html

from aim.emailer.base import Email, Advert, TopImage
from aim.news.models import NewsStory

logger = logging.getLogger(__name__)

TITLE = "News Email"
NEWS_SITES = ["BE", "JEP"]

# Initialize global email only once at start of session
if "global_email" not in st.session_state:
    st.session_state["global_email"] = Email(template_name="be_template.html")

# ---------------------------
# Helper functions
# ---------------------------

def get_global_email() -> Email:
    return st.session_state["global_email"]

def update_email_data(key: str, edited_df: pd.DataFrame) -> None:
    """Update the email data with the edited DataFrame."""
    if not edited_df.empty:
        get_global_email().update_data(key, edited_df.to_dict(orient="records"))

def render_data_editor(key: str) -> pd.DataFrame:
    """Render a data editor and return the edited DataFrame."""
    # Start with the current data
    df = pd.DataFrame(get_global_email().data[key])
    if df.empty:
        df = pd.DataFrame(columns=NewsStory.__annotations__.keys())

    # Sort by order if present (initial display)
    if "order" in df.columns:
        df["order"] = pd.to_numeric(df["order"], errors="coerce").fillna(0)
        df.sort_values("order", inplace=True)
        df = df[["order"] + [col for col in df.columns if col != "order"]]

    # Render the editor and capture the edited result
    edited_df = st.data_editor(
        df,
        key=key,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,  # Prevent index from appearing
    )

    # Sort the edited DataFrame before returning
    if "order" in edited_df.columns:
        edited_df["order"] = pd.to_numeric(edited_df["order"], errors="coerce").fillna(0)
        edited_df.sort_values("order", inplace=True)
        edited_df = edited_df[["order"] + [col for col in edited_df.columns if col != "order"]]

    return edited_df

# ---------------------------
# Initialize Session State
# ---------------------------

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

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

# Top image parameters
top_image_url = st.text_input("Top Image URL", key="top_image_url")
update_email_data("top_image_url", pd.DataFrame({"top_image_url": [top_image_url]}))

top_image_title = st.text_input("Top Image Title", key="top_image_title")
update_email_data("top_image_title", pd.DataFrame({"top_image_title": [top_image_title]}))

top_image_author = st.text_input("Top Image Author", key="top_image_author")
update_email_data("top_image_author", pd.DataFrame({"top_image_author": [top_image_author]}))

# Vertical Advert parameters
st.title("Vertical Adverts")
vertical_adverts_df = st.data_editor(
    pd.DataFrame(get_global_email().data["vertical_adverts"], columns=Advert.__annotations__.keys()),
    key="vertical_adverts",
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
)
update_email_data("vertical_adverts", vertical_adverts_df)

# ---------------------------
# Fetch Stories Button
# ---------------------------
if st.button("Fetch Stories"):
    with st.spinner("Fetching Stories..."):
        get_global_email().get_data(num_stories, num_business_stories, num_sports_stories)
    st.success("Stories fetched successfully!")

# Instructions
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
news_stories_df = render_data_editor("news_stories")
update_email_data("news_stories", news_stories_df)

business_stories_df = render_data_editor("business_stories")
update_email_data("business_stories", business_stories_df)

sport_stories_df = render_data_editor("sport_stories")
update_email_data("sport_stories", sport_stories_df)

# ---------------------------
# Render Email
# ---------------------------
if st.button("Render Email"):
    rendered_html = get_global_email().render()
    html(rendered_html, height=800, scrolling=True)
    if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
        st.success("Email saved successfully")