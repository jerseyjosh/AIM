from typing import Optional
import os
import asyncio

import jinja2

from aim.news.news_scraper import BEScraper, JEPScraper
from aim.weather.gov_je import GovJeWeather


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

class TopImage:
    def __init__(self, image_url: str, image_author: str):
        self.image_url = image_url
        self.image_author = image_author


class Advert:
    def __init__(self, url: str, image_url: str):
        self.url = url
        self.image_url = image_url


class Email:
    def __init__(self, template_name: str = "be_template.html"):
        self.template_name = template_name
        self.template_loader = jinja2.FileSystemLoader(TEMPLATES_DIR)
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["first_sentence"] = self.first_sentence
        self.template = self.template_env.get_template(self.template_name)

    def get_data(self, n_news: int, n_business: int, n_sports: int, site: str = "be"):
        """Async wrapper for getting news and business stories from the given site"""
        assert site in ["be", "jep"], "Site must be either 'be' or 'jep'"

        async def func():
            news_scraper = BEScraper() if site == "be" else JEPScraper()
            weather_scraper = GovJeWeather()
            # get data
            (
                news_stories,
                business_stories,
                sport_stories,
                weather_soup,
            ) = await asyncio.gather(
                news_scraper.get_n_stories_for_region("jsy", n_news),
                news_scraper.get_n_stories_for_region("jsy_business", n_business),
                news_scraper.get_n_stories_for_region("jsy_sport", n_sports),
                weather_scraper.get(),
            )
            # close the news scraper
            await news_scraper.close()
            # parse weather
            weather = weather_scraper.to_email(weather_soup)
            return news_stories, business_stories, sport_stories, weather

        # set internal data
        news_stories, business_stories, sport_stories, weather = asyncio.run(func())
        self.news_stories = news_stories
        self.business_stories = business_stories
        self.sport_stories = sport_stories
        self.weather = weather

    def render(self, save_path: Optional[str] = None, **kwargs) -> str:
        """Render the email template with the given context variables"""
        res = self.template.render(**kwargs)
        if save_path:
            with open(save_path, "w") as f:
                f.write(res)
        return res

    @staticmethod
    def first_sentence(x: str):
        """Helper jinja filter for getting first sentence of NewsStory.text"""
        splits = x.split(".")
        first = splits[0]
        if first:
            return first if first[-1] == "." else first + "."
        else:
            return ""


if __name__ == "__main__":
    email = Email()
