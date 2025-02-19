import asyncio

from aim.news.news_scraper import BEScraper
from aim.news.models import NewsStory

from aim.weather.gov_je import GovJeWeather

from aim.radio.voice import VoiceGenerator

class DailyNews:

    NUM_SENTENCES_PER_STORY = 1
    NUM_STORIES_PER_REGION = 2
    ELEVENLABS_TO_NAME = {
        "aim_christie": "Christie Bailey",
        "aim_jodie": "Jodie Yettram",
        "aim_fiona": "Fiona Potigny",
    }

    def __init__(self, speaker: str):
        self.speaker = speaker
        self.be_scraper = BEScraper()
        self.weather_scraper = GovJeWeather()

    async def close(self):
        await self.be_scraper.close()

    async def get_all_data(self):
        await asyncio.gather(
            self.get_news_stories(),
            self.get_weather()
        )

    async def get_news_stories(self) -> list[NewsStory]:
        jsy_stories, gsy_stories = await self.be_scraper.get_podcast_stories(self.NUM_STORIES_PER_REGION)
        self.stories = jsy_stories + gsy_stories
    
    async def get_weather(self) -> str:
        soup = await self.weather_scraper.get()
        weather = self.weather_scraper.to_radio(soup)
        weather = weather.strip()
        if weather[-1] != ".":
            weather += "."
        self.weather = weather

    def process_script(self, script: str) -> str:
        """Process the script to make it more radio-friendly"""
        # currently no preprocessing
        return script
        
    def make_script(self) -> str:
        # intro
        script = f"Bailiwick Radio News, I'm {self.ELEVENLABS_TO_NAME[self.speaker]}. Here are today's top stories.\n\n"
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
        return self.process_script(script)
        
if __name__ == "__main__":

    from pprint import pprint

    async def main():
        daily_news = DailyNews("AIM_christie")
        await daily_news.get_all_data()
        breakpoint()
        script = daily_news.make_script()
        pprint(script)

    asyncio.run(main())
        
