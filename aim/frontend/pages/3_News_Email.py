import os
import logging

import streamlit as st
from streamlit.components.v1 import html
import pandas as pd

from aim.emailer.base import Email, Advert
from aim.news.models import NewsStory

logger = logging.getLogger(__name__)

# Title
TITLE = "News Email"
NEWS_SITES = ['BE', 'JEP']

# init required session state
st.session_state.email_vars = {
    "weather": "",
    "news_stories": [],
    "business_stories": [],
    "sport_stories": [],
    "top_image_url": "",
    "top_image_title": "",
    "top_image_author": "",
    "vertical_adverts": [],
}

# Load Secrets
try:
    try:
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        STREAMLIT_USER = os.getenv("STREAMLIT_USER")
        STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")
        logger.debug("Secrets loaded from .env file")
    except Exception as e:
        STREAMLIT_USER = st.secrets["STREAMLIT_USER"]
        STREAMLIT_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]
        logger.debug("Secrets loaded from Streamlit Secrets")
except Exception as e:
    logger.error("Failed to load secrets")
    logger.error(e)

# Check if the user is logged in
if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False

# Login form
if st.session_state['logged_in'] is False:
    st.title(TITLE)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == STREAMLIT_USER and password == STREAMLIT_PASSWORD:
            st.session_state['logged_in'] = True
            st.success("Logged in.")
            st.rerun()
        else:
            st.error("Invalid username or password")

else:

    # Streamlit App Layout
    st.title(TITLE)

    # Boxes for email params
    num_stories = st.number_input("Number of News Stories", min_value=1, max_value=20, value=7, step=1)
    num_business_stories = st.number_input("Number of Business Stories", min_value=1, max_value=20, value=1, step=1)
    num_sports_stories = st.number_input("Number of Sports Stories", min_value=1, max_value=20, value=1, step=1)
    st.session_state.email_vars['top_image_url'] = st.text_input("Top Image URL")
    st.session_state.email_vars['top_image_title'] = st.text_input("Top Image Title")
    st.session_state.email_vars['top_image_author'] = st.text_input("Top Image Author")

    # Editable dataframe for advert banners
    st.header("Vertical Adverts")
    vertical_adverts = st.data_editor(
        pd.DataFrame({'url': [], 'image_url': []}, dtype='object'),
        key='vertical_banners',
        num_rows='dynamic',
        use_container_width=True
    )
    st.session_state.email_vars['vertical_adverts'] = [Advert(**item) for item in vertical_adverts.to_dict('records')]

    # Fetch stories button
    if st.button("Fetch Stories"):
        
        # Init email
        email = Email(template_name='be_template.html')

        # Fetch stories
        with st.spinner("Fetching Stories..."):
            email.get_data(num_stories, num_business_stories, num_sports_stories)
            st.session_state.email_vars['news_stories'] = email.news_stories
            st.session_state.email_vars['business_stories'] = email.business_stories
            st.session_state.email_vars['sport_stories'] = email.sport_stories
            st.session_state.email_vars['weather'] = email.weather

        # display news_stories df
        news_stories_df = st.data_editor(
            pd.DataFrame(st.session_state.email_vars.get('news_stories', [])),
            key='data_editor',
            num_rows='dynamic',
            use_container_width=True
        )
        st.session_state.email_vars['news_stories'] = (
            [NewsStory(**item) for item in news_stories_df.to_dict('records')]
            if len(news_stories_df) > 0
            else []
        )

        # display business_stories df
        business_stories_df = st.data_editor(
            pd.DataFrame(st.session_state.email_vars.get('business_stories', [])),
            key='business_data_editor',
            num_rows='dynamic',
            use_container_width=True
        )
        st.session_state.email_vars['business_stories'] = (
            [NewsStory(**item) for item in business_stories_df.to_dict('records')]
            if len(business_stories_df) > 0
            else []
        )

        # display sports stories df
        sports_stories_df = st.data_editor(
            pd.DataFrame(st.session_state.email_vars.get('sport_stories', [])),
            key='sport_data_editor',
            num_rows='dynamic',
            use_container_width=True
        )
        st.session_state.email_vars['sport_stories'] = (
            [NewsStory(**item) for item in sports_stories_df.to_dict('records')]
            if len(sports_stories_df) > 0
            else []
        )

        # Render the template with dynamic data.
        # For example, you might pass the stories and perhaps other context variables.
        rendered_html = email.render(**st.session_state.email_vars)

        # Display the rendered HTML in the Streamlit app.
        # Adjust the height as needed.
        html(rendered_html, height=800, scrolling=True)

        # save
        if st.download_button("Save Email", rendered_html, f"email.html", "Save"):
            st.success("Email saved successfully")
