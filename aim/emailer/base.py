from typing import Optional
import os
import asyncio
import logging
import jinja2
from dataclasses import dataclass

from aim.news.news_scraper import BEScraper, JEPScraper
from aim.weather.gov_je import GovJeWeather
from aim.family_notices import FamilyNotices

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

@dataclass
class TopImage:
    image_url: str
    image_author: str

@dataclass
class Advert:
    url: str
    image_url: str


class Email:

    # Jinja variables that need to be passed to the template
    # these should be checked to ensure they are the only keys in self.data

    def __init__(self, template_name: str = "be_template.html"):

        # load jinja env/templates
        self.template_name = template_name
        self.template_loader = jinja2.FileSystemLoader(TEMPLATES_DIR)
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["first_sentence"] = self.first_sentence
        self.template = self.template_env.get_template(self.template_name)

        # Store email data as a dictionary (used in Streamlit)
        self.data = {
            "news_stories": [],
            "business_stories": [],
            "sport_stories": [],
            "weather": None,
            "family_notices": [],
            "top_image_url": "",
            "top_image_title": "",
            "top_image_author": "",
            "vertical_adverts": [],
        }

    async def _get_data_wrapper(self, site: str, n_news: int, n_business: int, n_sports: int):
        """Fetch data from multiple sources asynchronously."""
        assert site in ["be", "jep"], "Site must be either 'be' or 'jep'"

        news_scraper = BEScraper() if site == "be" else JEPScraper()
        weather_scraper = GovJeWeather()
        family_notices_scraper = FamilyNotices()

        SCRAPER_TASKS = {
            "news_stories": news_scraper.get_n_stories_for_region("jsy", n_news),
            "business_stories": news_scraper.get_n_stories_for_region("jsy_business", n_business),
            "sport_stories": news_scraper.get_n_stories_for_region("jsy_sport", n_sports),
            "connect_cover_image": news_scraper.get_connect_cover(),
            "weather_soup": weather_scraper.get(),
            "family_notices": family_notices_scraper.get_notices(),
        }

        results = await asyncio.gather(*SCRAPER_TASKS.values(), return_exceptions=True)

        await asyncio.gather(news_scraper.close(), family_notices_scraper.close())

        data = dict(zip(SCRAPER_TASKS.keys(), results))

        # Convert weather data
        data["weather"] = weather_scraper.to_email(data["weather_soup"])
        del data["weather_soup"]

        # Handle errors
        for key, result in data.items():
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {key}: {result}")
                data[key] = None  

        return data

    def get_data(self, n_news: int, n_business: int, n_sports: int, site: str = "be"):
        """Sync wrapper to fetch data and store it as an instance attribute."""
        self.data = asyncio.run(self._get_data_wrapper(site, n_news, n_business, n_sports))

    def update_data(self, key: str, value):
        """Manually update the data object for external changes (e.g., from Streamlit)."""
        assert key in self.data.keys(), f"Key '{key}' not expected in Jinja vars"
        self.data[key] = value

    def render(self) -> str:
        """Render the email template with the given data."""
        return self.template.render(**self.data)

    @staticmethod
    def first_sentence(x: str):
        """Extract the first sentence of a string."""
        if not x:
            return ""
        first = x.split(".")[0]
        return first + "." if first and first[-1] != "." else first
    
if __name__ == "__main__":
    breakpoint()
    Advert.__annotations__