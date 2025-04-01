import uvloop
import os
import logging
from datetime import datetime

import streamlit as st

from aim.radio.daily_news import DailyNews
from aim.radio.voice import VoiceGenerator

logger = logging.getLogger(__name__)

# Set valid speakers
VALID_SPEAKERS = ['aim_christie', 'aim_jodie', 'aim_jodie_2']
TITLE = "Daily News Podcast"

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
    # Function to generate the script
    def generate_script(speaker: str):
        async def _generate_script(speaker: str):
            # gather data and make script
            daily_news = DailyNews(speaker)
            await daily_news.get_all_data()
            script = daily_news.make_script()
            await daily_news.close()
            return script
        return uvloop.run(_generate_script(speaker))

    # Streamlit App Layout
    st.title("Daily News Podcast")

    # Dropdown Menu for settings
    speaker_selection = st.selectbox(
        "Select a speaker:", 
        VALID_SPEAKERS, 
        help="Select the setting for the script generation"
    )

    # "Generate Script" button
    if st.button("Generate Script"):
        # Call your function to generate the script based on the selected dropdown option
        with st.spinner("Locating Articles..."):
            script = generate_script(speaker_selection)  # Replace with your function call
        st.session_state['script'] = script  # Store the script in session state

    # Editable text box populated with the generated script
    script_text = st.text_area("Script Editor", value=st.session_state.get('script', ''), height=300)

    # initialize voice generator
    voice_generator = VoiceGenerator(ELEVENLABS_API_KEY)
    # Show remaining credits
    user = voice_generator.client.user.get()
    used_characters_pct = f'{user.subscription.character_count / user.subscription.character_limit:.2%}'
    reset_date_int = user.subscription.next_character_count_reset_unix
    reset_date_strftime = datetime.fromtimestamp(reset_date_int).strftime('%Y-%m-%d %H:%M:%S')
    st.info(f"AI Speech Used Characters: {user.subscription.character_count:,}/{user.subscription.character_limit:,} ({used_characters_pct}), usage resets {reset_date_strftime}")

    # "Generate Podcast" button
    if st.button("Generate Podcast"):
        if script_text:
            # Call function to generate the podcast, passing the current script text
            with st.spinner("Generating Podcast..."):
                audio = voice_generator.generate(script_text, speaker_selection)
            with st.spinner("Preparing file for download..."):
                output = b"".join(audio)
            # Provide download link for the generated MP3 file
            st.audio(output, format="audio/mpeg")
        else:
            st.warning("Please generate and edit the script before generating the podcast.")
