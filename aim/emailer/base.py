from typing import Optional, Dict, List, Any
import os
import asyncio
import uvloop
import logging
import jinja2
from dataclasses import dataclass
from datetime import datetime

from aim.news.news_scraper import BEScraper, JEPScraper
from aim.weather.gov_je import GovJeWeather
from aim.family_notices import FamilyNotices

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

@dataclass
class Advert:
    url: str
    image_url: str

class Email:
    """Manages email template rendering and data fetching."""
    def __init__(self, template_name: str = "be_template.html"):
        self.template_name = template_name
        self.template_loader = jinja2.FileSystemLoader(TEMPLATES_DIR)
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["first_sentence"] = self.first_sentence
        self.template = self.template_env.get_template(self.template_name)

        # Initialize data with default empty structures
        self.data: Dict[str, Any] = {
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

    async def _get_data_wrapper(self, site: str, n_news: int, n_business: int, n_sports: int, deaths_start: datetime, deaths_end: datetime) -> Dict[str, Any]:
        """Fetch data from multiple sources asynchronously."""
        if site not in ["be", "jep"]:
            raise ValueError("Site must be either 'be' or 'jep'")

        news_scraper = BEScraper() if site == "be" else JEPScraper()
        weather_scraper = GovJeWeather()
        family_notices_scraper = FamilyNotices()

        tasks = {
            "news_stories": news_scraper.get_n_stories_for_region("jsy", n_news),
            "business_stories": news_scraper.get_n_stories_for_region("jsy_business", n_business),
            "sport_stories": news_scraper.get_n_stories_for_region("jsy_sport", n_sports),
            "connect_cover_image": news_scraper.get_connect_cover(),
            "weather_soup": weather_scraper.get(),
            "family_notices": family_notices_scraper.get_notices(deaths_start, deaths_end),
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        await asyncio.gather(news_scraper.close(), family_notices_scraper.close())

        data = dict(zip(tasks.keys(), results))

        # Process weather data
        try:
            data["weather"] = weather_scraper.to_email(data["weather_soup"])
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            data["weather"] = None
        del data["weather_soup"]

        # Handle exceptions in results
        for key, result in data.items():
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {key}: {result}")
                data[key] = [] if key in ["news_stories", "business_stories", "sport_stories", "family_notices"] else None

        return data

    def get_data(self, n_news: int, n_business: int, n_sports: int, deaths_start: datetime, deaths_end: datetime, site: str = "be") -> None:
        """Synchronously fetch data and update instance state."""
        try:
            fetched_data = uvloop.run(self._get_data_wrapper(site, n_news, n_business, n_sports, deaths_start, deaths_end))
            self.data.update(fetched_data)
        except Exception as e:
            logger.error(f"Error in get_data: {e}")
            raise

    def update_data(self, key: str, value: Any) -> None:
        """Update a specific key in the data dictionary."""
        if key not in self.data:
            raise KeyError(f"Key '{key}' not expected in email data")
        self.data[key] = value

    def render(self) -> str:
        """Render the email template with the current data."""
        return self.template.render(**self.data)

    @staticmethod
    def first_sentence(text: Optional[str]) -> str:
        """Extract the first sentence from a string."""
        if not text:
            return ""
        first = text.split(".")[0]
        return first + "." if first and not first.endswith(".") else first