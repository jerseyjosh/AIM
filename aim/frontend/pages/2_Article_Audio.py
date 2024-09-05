# import os
# import logging
# import asyncio

# import streamlit as st

# from aim.news.news_scraper import BEScraper
# from aim.news.models import NewsStory

# logger = logging.getLogger(__name__)

# st.title("Article Audio")

# # Load Secrets
# try:
#     try:
#         from dotenv import load_dotenv, find_dotenv
#         load_dotenv(find_dotenv())
#         ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
#         STREAMLIT_USER = os.getenv("STREAMLIT_USER")
#         STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")
#         logger.debug("Secrets loaded from .env file")
#     except Exception as e:
#         ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
#         STREAMLIT_USER = st.secrets["STREAMLIT_USER"]
#         STREAMLIT_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]
#         logger.debug("Secrets loaded from Streamlit Secrets")
# except Exception as e:
#     logger.error("Failed to load secrets")
#     logger.error(e)

# # Check if the user is logged in
# if "logged_in" not in st.session_state:
#     st.session_state['logged_in'] = False

# # Login form
# if st.session_state['logged_in'] is False:
#     username = st.text_input("Username")
#     password = st.text_input("Password", type="password")
#     if st.button("Login"):
#         if username == STREAMLIT_USER and password == STREAMLIT_PASSWORD:
#             st.session_state['logged_in'] = True
#             st.success("Logged in.")
#             st.rerun()
#         else:
#             st.error("Invalid username or password")

# else:
#     # Function to fetch news story
#     def fetch_news_story(url: str):
#         async def func(url):
#             scraper = BEScraper()
#             news_story = scraper.get_news_story_from_url(url)
#             await scraper.close()
#             return news_story
#         return asyncio.run(func(url))

#     # Url iput
#     url = st.text_input("BailiwickExpress Article URL")
#     if st.button("Fetch News Story"):
#         with st.spinner("Fetching news story..."):
#             news_story = fetch_news_story(url)
#             article_body, article_author = news_story.text, news_story.author
#             st.session_state['news_story'] = news_story
    
#     # Display article Text    
#     if st.session_state.get('news_story'):
#         article_text = st.text_area("Article Editor", value=st.session_state.get('news_story', '').text, height=300)

    