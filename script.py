from typing import Optional, List
import logging

from elevenlabs.client import ElevenLabs
from elevenlabs import save

from weather import WeatherScraper, WeatherReport
from news import NewsScraper, NewsStory
from translate import Translator

logger = logging.getLogger(__name__)

class Script:
    def __init__(
            self, 
            speaker: str,
            elevenlabs_api_key: str,
            news_stories: Optional[List[NewsStory]] = None,
            weather: Optional[WeatherReport] = None,
        ):
        self.speaker = speaker
        self.news_stories = news_stories
        self.weather = weather
        self.text = None
        self.weather_scraper = WeatherScraper()
        self.news_scraper = NewsScraper()
        self.elevenlabs = ElevenLabs(api_key=elevenlabs_api_key)
        self.translator = Translator()
        self.voice_id = self._get_voice_id()

    def _get_voice_id(self):
        voices = self.elevenlabs.voices.get_all().voices
        for v in voices:
            if v.name.lower() == f'aim {self.speaker}':
                return v.voice_id
        raise ValueError(f"Speaker {self.speaker} not found in available voices.")

    def get_weather(self):
        self.weather: WeatherReport = self.weather_scraper.get()

    def get_news(self):
        self.news_stories: List[NewsStory] = self.news_scraper.get()

    def make_text(self):
        # get news stories if not set
        if not self.news_stories:
            self.get_news()
        # get weather report if not set
        if not self.weather:
            self.get_weather()
        intro = f"Bailiwick Radio News, I'm {self.speaker}."
        body = " ".join([str(n)for n in self.news_stories])
        read_more = f"To find out more about this, and other stories, visit bailiwick express dot com."
        weather = f"Now the weather for today: {self.weather}."
        outro = "Bailiwick, radio, news."
        self.text = intro + body + read_more + weather + outro

    def generate_audio(self, text):
        return self.elevenlabs.generate(
            text=text,
            voice_id=self.voice_id,
            model='eleven_multilingual_v2'
        )

    def save_audio(self, output: str = None):
        if not self.text:
            raise ValueError("Text not generated yet. Run make_text() first.")
        if not output:
            output = f"{self.speaker}_news.mp3"
        audio = self.generate_audio(self.text)
        save(audio, output)


# if __name__=="__main__":
#     load_dotenv()
#     api_key = os.getenv("ELEVENLABS_API_KEY")
#     client = ElevenLabs(api_key=api_key)
#     breakpoint()

