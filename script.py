from typing import Optional, List
import logging
from datetime import datetime
import re

from elevenlabs.client import ElevenLabs
from elevenlabs import save

from weather import WeatherScraper, WeatherReport
from news import NewsScraper, NewsStory
from llm import LLM

logger = logging.getLogger(__name__)


class Script:
    def __init__(
            self, 
            speaker: str,
            elevenlabs_api_key: str,
            openai_api_key: str = None,
            news_stories: Optional[List[NewsStory]] = None,
            weather: Optional[WeatherReport] = None,
        ):
        self.speaker = speaker
        self.news_stories = news_stories
        self.weather = weather
        self.text = None
        self.audio = None
        self.weather_scraper = WeatherScraper()
        self.news_scraper = NewsScraper()
        self.elevenlabs = ElevenLabs(api_key=elevenlabs_api_key)
        self.llm = LLM(openai_api_key=openai_api_key) if openai_api_key else None
        self.voice_id = self.get_voice_id()
        self.language = "english"

    def get_voice_id(self):
        voices = self.elevenlabs.voices.get_all().voices
        for v in voices:
            if v.name.lower() == f'aim {self.speaker}':
                return v.voice_id
        raise ValueError(f"Speaker {self.speaker} not found in available voices.")

    def get_weather(self):
        self.weather: WeatherReport = self.weather_scraper.get()

    def get_news(self):
        self.news_stories: List[NewsStory] = self.news_scraper.get()

    def make_text(self, language: str = "english", model: str = "gpt-4o"):

        # validate language
        assert language in LLM.LANGUAGES, "Invalid language. Choose from: " + ', '.join(LLM.LANGUAGES)

        # get news stories if not set
        if not self.news_stories:
            self.get_news()
            jsy_stories = [s for s in self.news_stories if s.region == 'jsy']
            gsy_stories = [s for s in self.news_stories if s.region == 'gsy']

        # get weather report if not set
        if not self.weather:
            self.get_weather()

        # make script
        intro = f"Bailiwick Radio News, I'm {self.speaker}. "
        body = "In jersey, "
        for i, story in enumerate(jsy_stories):
            body += story.text
            if i<len(jsy_stories)-1:
                body += "Meanwhile, "
        body += 'In guernsey, '
        for i, story in enumerate(gsy_stories):
            body += story.text
            if i<len(gsy_stories)-1:
                body += "Finally, "
        read_more = f"To find out more about this, and other stories, visit bailiwick express dot com."
        weather = f"Now the weather for today: {self.weather}.."
        outro = "Bailiwick radio news."
        text = intro + body + read_more + weather + outro

        # process text
        self.text = self.llm.process(text, language, model)

    def make_audio(self):
        assert self.text is not None, "Text not generated yet. Run make_text() first."
        self.audio = self.elevenlabs.generate(
            text=self.text,
            voice=self.voice_id,
            model='eleven_multilingual_v2'
        )

    def save_audio(self, output: str = None):
        assert self.audio is not None, "Audio not generated yet. Run make_audio() first."
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        if not self.text:
            raise ValueError("Text not generated yet. Run make_text() first.")
        if not output:
            output = '_'.join(self.speaker.split(' ') + [self.language, timestamp]) + '.mp3'
        save(self.audio, output)


# if __name__=="__main__":
#     from dotenv import load_dotenv
#     import os
#     import argparse

#     # load dotenv
#     load_dotenv()

#     script = Script(
#         speaker="christie bailey",
#         elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
#         openai_api_key=os.getenv("OPENAI_API_KEY"),
#     )

#     script.make_text()
#     breakpoint()
