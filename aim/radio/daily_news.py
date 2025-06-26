import asyncio
import logging

from aim.news.bailiwick_express_scraper import BEScraper
from aim.news.models import NewsStory

from aim.weather.gov_je import GovJeWeather
from aim.radio.voice import VoiceGenerator

logger = logging.getLogger(__name__)

class DailyNews:

    NUM_SENTENCES_PER_STORY = 1
    NUM_STORIES_PER_REGION = 2

    def __init__(self, speaker: str):
        self.speaker = speaker
        self.be_scraper = BEScraper()
        self.weather_scraper = GovJeWeather()
        logger.info(f"DailyNews initialized with speaker: {speaker}")

    @staticmethod
    def elevenlabs_to_name(speaker: str) -> str:
        if 'christie' in speaker:
            return "Christie Bailey"
        elif 'jodie' in speaker:
            return "Jodie Yettram"
        elif 'fiona' in speaker:
            return "Fiona Potigny"
        else:
            raise ValueError(f"Speaker {speaker} not recognized")

    async def close(self):
        logger.info("Closing resources")
        await self.be_scraper.close()

    async def get_all_data(self):
        logger.info("Fetching all data")
        await asyncio.gather(
            self.get_news_stories(),
            self.get_weather()
        )
        logger.info("All data fetched successfully")

    async def get_news_stories(self) -> list[NewsStory]:
        logger.info(f"Fetching news stories, {self.NUM_STORIES_PER_REGION} per region")
        jsy_stories, gsy_stories = await self.be_scraper.get_podcast_stories(self.NUM_STORIES_PER_REGION)
        self.stories = jsy_stories + gsy_stories
        logger.info(f"Retrieved {len(self.stories)} stories total")
    
    async def get_weather(self) -> str:
        logger.info("Fetching weather information")
        soup = await self.weather_scraper.get()
        weather = self.weather_scraper.to_radio(soup)
        weather = weather.strip()
        if weather[-1] != ".":
            weather += "."
        self.weather = weather
        logger.info("Weather data processed successfully")

    def process_script(self, script: str) -> str:
        """Process the script to make it more radio-friendly"""
        logger.debug("Processing script")
        # currently no preprocessing
        return script
        
    def make_script(self) -> str:
        logger.info("Generating news script")
        # intro
        script = f"Bailiwick Radio News, I'm {self.elevenlabs_to_name(self.speaker)}. Here are today's top stories.\n\n"
        # stories
        for i,story in enumerate(self.stories):
            if i == 1:
                script += "In other news, "
            if i == 2:
                script += "Meanwhile in Guernsey, "
            if i == 3:
                script += "Also in Guernsey, "
            first_sentences = '. '.join(story.text.split(".")[:self.NUM_SENTENCES_PER_STORY])
            script += f"{first_sentences}.\n\n"
        # strapline
        script += "For more on all these stories, visit Bailiwick Express dot com.\n\n"
        # weather
        script += f"Now for the weather. {self.weather}\n\n"
        # outro
        script += "You're up to date with Bailiwick Radio News."
        logger.info(f"Script generated, length: {len(script)} characters")
        return self.process_script(script)
        
if __name__ == "__main__":

    from pprint import pprint
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('websockets').setLevel(logging.CRITICAL)

    async def main():
        logger.info("Starting DailyNews script generation")
        daily_news = DailyNews("aim_christie")
        await daily_news.get_all_data()
        script = daily_news.make_script()
        pprint(script)
        logger.info("Script generation complete")

    import uvloop
    uvloop.run(main())
