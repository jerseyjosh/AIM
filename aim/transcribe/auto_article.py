import os
import apps as st
from dotenv import load_dotenv, find_dotenv
import assemblyai as aai
import openai
import whisper

# Load environment variables
load_dotenv(find_dotenv())

# Set up AssemblyAI
aai.settings.api_key = os.getenv("ASSEMBLY_KEY")

# def transcribe_audio(file_path):
#     config = aai.TranscriptionConfig()
#     transcriber = aai.Transcriber()
#     transcript = transcriber.transcribe(file_path, config)
#     return transcript.text

def transcribe_audio(file_path, size='base'):
    model = whisper.load_model(size)
    result = model.transcribe(file_path)
    return result['text']

def generate_article(transcription, additional_context):
    client = openai.OpenAI(
        api_key=os.environ.get("OPENAI_KEY"),
    )
    messages = [
        {
            "role": "system",
            "content": 
                """
                You are a professional journalist writing for a large newspaper about La Saisone Francaise.
                You will receive a transcription of a piece of media (e.g. a press conference, a conversation, court proceedings).
                Output a markdown formatted, long-form article, with only headers and paragraphs, based on the content of the transcription.
                Utilise additional context if provided.
                Preserve french phrases.
                You do not need to mention Jersey specifically as it is implied.
                Keep output factual, neutral and professional, avoiding any emotional phrases like "in a shocking turn of events", "surprisingly", etc.
                """
        },
        {
            "role": "user",
            "content": f"Transcription:\n\n{transcription}"
        }
    ]
    if additional_context:
        messages.append(
            {
                "role": "user",
                "content": f"Additional context:\n\n{additional_context}"
            }
        )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    article = response.choices[0].message.content
    return article

# Streamlit app
st.title("Auto-Article")

# Input for local file path
file_path = st.text_input("Enter the local path to the MP4 file:")

if file_path:
    st.video(file_path)

# Transcribe button
if st.button("Transcribe"):
    if file_path:
        with st.spinner("Transcribing..."):
            transcription = transcribe_audio(file_path)
        
        st.success("Transcription complete!")
        st.text_area("Transcription:", value=transcription, height=300)
        
        # Store the transcription in session state for later use
        st.session_state.transcription = transcription
    else:
        st.error("Please enter a valid file path.")

st.markdown("---")

# Input for additional context
additional_context = st.text_area("Enter any additional context information (optional):")

# Generate Article button
if st.button("Generate Article"):
    if 'transcription' in st.session_state:
        with st.spinner("Generating article..."):
            article = generate_article(st.session_state.transcription, additional_context)
        
        st.success("Article generated!")
        st.markdown(article)
    else:
        st.error("Please transcribe an audio file first.")
