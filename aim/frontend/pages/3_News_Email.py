import asyncio
import os
import logging

import streamlit as st
import pandas as pd

from aim.news.news_scraper import BEScraper
import aim.emailer  # import the emailer package so we can get its path

# Import Jinja2 and Streamlit components for HTML rendering
from jinja2 import Environment, FileSystemLoader
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

# Title
TITLE = "News Email"
NEWS_SITES = ['BE', 'JEP']

# Load Secrets
try:
    try:
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
        STREAMLIT_USER = os.getenv("STREAMLIT_USER")
        STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")
        logger.debug("Secrets loaded from .env file")
    except Exception as e:
        ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
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

    # Async wrapper to get stories
    def get_stories(n_stories: int):
        async def func():
            scraper = BEScraper()
            stories = await scraper.get_n_stories_for_region('jsy', n_stories)
            await scraper.close()
            return stories
        return asyncio.run(func())

    # Streamlit App Layout
    st.title("News Email")

    # Button to fetch stories
    num_stories = st.number_input("Number of Stories", min_value=1, max_value=20, value=7, step=1)
    if st.button("Fetch Stories"):
        with st.spinner("Fetching Stories..."):
            stories = get_stories(num_stories)
            stories_df = pd.DataFrame(stories)
            stories_df['ordering'] = None
            st.session_state.stories_df = pd.DataFrame(stories)

    # # Box to add top_image_url and top_image_author
    # st.session_state.top_image_url = st.text_input("Top Image URL")
    # st.session_state.top_image_author = st.text_input("Top Image Author")

    # If stories exist, allow editing
    if 'stories_df' in st.session_state:
        edited_df = st.data_editor(
            st.session_state.stories_df,
            key='data_editor',
            num_rows='dynamic',
            use_container_width=True
        )
        st.session_state.stories_df = edited_df

        # ----- Render HTML from Jinja2 Template -----
        # Build the absolute path to the templates folder in the emailer package.
        templates_dir = os.path.join(os.path.dirname(aim.emailer.__file__), "templates")
        # Create the Jinja2 environment with a FileSystemLoader
        env = Environment(loader=FileSystemLoader(templates_dir))
        env.filters['first_sentence'] = lambda text: text.split('.')[0] + '.'
        # Load the template file; for example, "template1.html"
        template = env.get_template("be_template.html")

        # Convert the edited DataFrame to a list of dictionaries.
        # (Adjust the field names as needed to match your template.)
        stories_list = st.session_state.stories_df.to_dict("records")

        # Render the template with dynamic data.
        # For example, you might pass the stories and perhaps other context variables.
        rendered_html = template.render(
            title=TITLE,
            news_stories=stories_list
        )

        # Display the rendered HTML in the Streamlit app.
        # Adjust the height as needed.
        components.html(rendered_html, height=600, scrolling=True)
