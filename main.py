from dotenv import load_dotenv
import os
import argparse

from script import Script
from weather import WeatherScraper
from news import NewsStory


if __name__=="__main__":

    # load dotenv
    load_dotenv()

    # argparse
    parser = argparse.ArgumentParser(description="Generate audio from a script")
    parser.add_argument("--speaker", type=str, help="The speaker name", required=True)
    args = parser.parse_args()

    # filler stories:
    news_stories = [
        NewsStory("Durrell has hit back at the rebel members looking to oust the charity's trustees, claiming that the amount of money that the zoo has spent dealing with this group has been 'extremely high' – and that the group attempted to 'coerce' the charity into accepting two of its own members onto the board. In a post on social media this morning, members of the 'We Love the Zoo' group raised concerns about the zoo's animal management, procurement processes, and financial performance."),
        NewsStory("A 19-year-old man has been charged with grave and criminal assault following an alleged incident at Lilly’s Mini Market earlier this week.Joseph Ross Jordan from Glasgow was arrested following the alleged assault on Thursday evening. He is due to appear in the Magistrate's Court on Monday. Police are still seeking information regarding one of the men in an appeal issued yesterday.")
    ]

    script = Script(
        speaker=args.speaker,
        news_stories=news_stories,
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY")
    )
    script.make_text()
    script.save_audio()