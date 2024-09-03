import asyncio

from aim.news.news_scraper import BEScraper
from aim.news.models import NewsStory

from aim.weather.gov_je import GovJeWeather

from aim.radio.voice import ElevenLabs

class DailyNews:

    NUM_SENTENCES_PER_STORY = 1
    NUM_STORIES_PER_REGION = 2
    ELEVENLABS_TO_NAME = {
        "AIM_christie": "Christie Bailey",
        "AIM_jodie": "Jodie Yettram",
        "AIM_fiona": "Fiona Potigny",
    }

    def __init__(self, elevenlabs_name: str):
        self.elevenlabs_name = elevenlabs_name
        self.be_scraper = BEScraper()
        self.weather_scraper = GovJeWeather()
        self.voice = ElevenLabs(elevenlabs_name)

    async def get_all_data(self):
        await asyncio.gather(
            self.get_news_stories(self.NUM_STORIES_PER_REGION),
            self.get_weather()
        )

    async def get_news_stories(self, n_stories: int) -> list[NewsStory]:
        jsy_stories, gsy_stories = await asyncio.gather(
            self.be_scraper.get_all_stories_from_n_pages("jsy", 1),
            self.be_scraper.get_all_stories_from_n_pages("gsy", 1)
        )
        self.stories = jsy_stories[:self.NUM_STORIES_PER_REGION] + gsy_stories[:self.NUM_STORIES_PER_REGION]
    
    async def get_weather(self) -> str:
        weather = await self.weather_scraper.get()
        weather = weather.strip()
        if weather[-1] != ".":
            weather += "."
        self.weather = weather
        
    def make_script(self) -> str:
        script = f"Bailwick Radio News, I'm {self.ELEVENLABS_TO_NAME[self.elevenlabs_name]}. Here are today's top stories. "
        for i,story in enumerate(self.stories):
            if i == 1:
                script += "In other news, "
            if i == 2:
                script += "Meanwhile in Guernsey, "
            if i == 3:
                script += "Also in Guernsey, "
            first_sentences = '. '.join(story.text.split(".")[:self.NUM_SENTENCES_PER_STORY])
            script += f"{first_sentences}. "
        script += f"Now for the weather. {self.weather} "
        self.script = script
        self.script += "Bailiwick... Radio... News. "
        
if __name__ == "__main__":

    from pprint import pprint

    async def main():
        daily_news = DailyNews("AIM_christie")
        await daily_news.get_all_data()
        daily_news.make_script()
        pprint(daily_news.script)
        breakpoint()

    asyncio.run(main())
        
