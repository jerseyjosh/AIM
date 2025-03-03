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
EMAIL = Email(template_name="be_template.html")

# ---------------------------
# Helper functions
# ---------------------------

def update_email_vars():
    # iterate keys required to update
    for key in EMAIL.data.keys():
        # if we have local version of data, update email
        if key in st.session_state:
            internal = st.session_state[key]
            if isinstance(internal, pd.DataFrame):
                # convert to list of dictionaries
                internal = internal.to_dict(orient="records")
            EMAIL.update_data(key, internal)

def render_data_editor(key):
    # reorder such that order is first
    columns = list(NewsStory.__annotations__.keys())
    if 'order' in columns:
        columns.remove('order')
        columns = ['order'] + columns
    return st.data_editor(
        pd.DataFrame(EMAIL.data[key])[columns],
        key=key,
        num_rows="dynamic",
        use_container_width=True,
        on_change=update_email_vars,
    )


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

# Top image parameters
st.text_input("Top Image URL", key="top_image_url", on_change=update_email_vars)
st.text_input("Top Image TItle", key="top_image_title", on_change=update_email_vars)
st.text_input("Top Image Author", key="top_image_author", on_change=update_email_vars)

# Vertical Advert parameters
st.title("Vertical Adverts")
st.data_editor(
    pd.DataFrame(EMAIL.data["vertical_adverts"], columns=Advert.__annotations__.keys()),
    key="vertical_adverts",
    num_rows="dynamic",
    use_container_width=True,
    on_change=update_email_vars,
)

# ---------------------------
# Fetch Stories Button
# ---------------------------
if st.button("Fetch Stories"):

    with st.spinner("Fetching Stories..."):

        # Get all data
        EMAIL.get_data(num_stories, num_business_stories, num_sports_stories)

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

render_data_editor("news_stories")
render_data_editor("business_stories")
render_data_editor("sport_stories")

# ---------------------------
# Render Email
# ---------------------------
if st.button("Render Email"):

    # Reuse the same Email object to render
    email = Email(template_name="be_template.html")
    rendered_html = email.render(**st.session_state["email_vars"])

    # Display the rendered HTML in the Streamlit app
    html(rendered_html, height=800, scrolling=True)

    # Provide a download button
    if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
        st.success("Email saved successfully")
