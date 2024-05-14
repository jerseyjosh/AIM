from dotenv import load_dotenv
import os
import argparse
import logging
import datetime
from tqdm.auto import tqdm

from script import Script
from weather import WeatherScraper
from news import NewsStory


if __name__=="__main__":

    # set up logging
    logging.basicConfig(level=logging.INFO)

    # load dotenv
    load_dotenv()

    # argparse
    parser = argparse.ArgumentParser(description="Generate audio from a script")
    parser.add_argument("--speaker", type=str, help="The speaker name", required=True)
    parser.add_argument("--language", type=str, help="The language to translate to", default=None)
    args = parser.parse_args()

    script = Script(
        speaker=args.speaker,
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # script.make_text(translate_to=args.language)
    # script.make_audio()
    # script.save_audio()

    for language in tqdm(["english", "french", "portuguese", "polish", "romanian"]):
        script.make_text(translate_to=language)
        script.make_audio()
        script.save_audio()