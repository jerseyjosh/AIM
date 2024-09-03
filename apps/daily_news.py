import streamlit as st
from aim.radio.daily_news import DailyNews

def generate_script(speaker: str):
    daily_news = DailyNews(speaker.lower())
    daily_news.get_all_data()
    daily_news.make_script()
    return daily_news.script

# Define the settings for the dropdown menu
dropdown_options = ["AIM_christie" , "AIM_jodie", "AIM_fiona"]

# Streamlit App Layout
st.title("News to Podcast Generator")

# Dropdown Menu for settings
selected_option = st.selectbox("Select a setting:", dropdown_options, help="Select the setting for the script generation")

# "Generate Script" button
if st.button("Generate Script"):
    # Call your function to generate the script based on the selected dropdown option
    script = generate_script(selected_option)  # Replace with your function call
    st.session_state['script'] = script  # Store the script in session state

# Editable text box populated with the generated script
script_text = st.text_area("Script Editor", value=st.session_state.get('script', ''), height=300)

# "Generate Podcast" button
if st.button("Generate Podcast"):
    pass
    # if script_text:
    #     # Call your function to generate the podcast, passing the current script text
    #     podcast_file = generate_podcast(script_text)  # Replace with your function call
    #     # Provide download link for the generated MP3 file
    #     st.download_button("Download Podcast", podcast_file, file_name="podcast.mp3", mime="audio/mpeg")
    # else:
    #     st.warning("Please generate and edit the script before generating the podcast.")
