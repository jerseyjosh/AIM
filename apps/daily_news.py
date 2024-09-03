import asyncio
import os

import streamlit as st

from aim.radio.daily_news import DailyNews
from aim.radio.voice import VoiceGenerator

# Load Secrets
try:
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
except Exception as e:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

VALID_SPEAKERS = ['aim_christie', 'aim_jodie', 'aim_fiona']

# Function to generate the script
def generate_script(speaker: str):
    async def _generate_script(speaker: str):
        # gather data and make script
        daily_news = DailyNews(speaker)
        await daily_news.get_all_data()
        script = daily_news.make_script()
        await daily_news.close()
        return script
    return asyncio.run(_generate_script(speaker))

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

# "Generate Podcast" button
if st.button("Generate Podcast"):
    if script_text:
        # Call your function to generate the podcast, passing the current script text
        voice_generator = VoiceGenerator(ELEVENLABS_API_KEY)
        with st.spinner("Generating Podcast..."):
            audio = voice_generator.generate(script_text, speaker_selection)
        with st.spinner("Preparing file for download..."):
            output = b"".join(audio)
        # Provide download link for the generated MP3 file
        st.audio(output, format="audio/mpeg")
        #st.download_button("Download", output, file_name=f"{speaker_selection}_news.mp3", mime="audio/mp3")
    else:
        st.warning("Please generate and edit the script before generating the podcast.")
