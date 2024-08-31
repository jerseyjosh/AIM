from abc import ABC, abstractmethod
from typing import Union

import logging
import asyncio
import re
from tenacity import retry, stop_after_attempt, wait_random_exponential

import aiohttp
from urllib.parse import urljoin
import aiolimiter
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio

from news.models import NewsStory

logger = logging.getLogger(__name__)

class BaseScraper(ABC):

    def __init__(self, requests_per_period: int = 100, period_seconds: int = 1):
        self.session = aiohttp.ClientSession()
        self.limiter = aiolimiter.AsyncLimiter(max_rate = requests_per_period, time_period = period_seconds)
        logger.debug("Scraper initialised with limits: requests_per_period = {requests_per_period}, period_seconds = {period_seconds}")

    @retry(stop=stop_after_attempt(10), wait=wait_random_exponential(multiplier=1, max=60))
    async def fetch(self, url) -> BeautifulSoup:
        """
        Scrape a url and return the BeautifulSoup object.
        """
        try:
            if self.limiter:
                async with self.limiter:
                    async with self.session.get(url) as response:
                        response.raise_for_status()
                        html = await response.text()
                        return BeautifulSoup(html, "html.parser")
            else:
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()
                    return BeautifulSoup(html, "html.parser")
        except Exception as e:
            logger.exception(f"Error fetching url {url}: {e}")
            return None
            
    async def fetch_all(self, urls: Union[str, list[str]]) -> list[BeautifulSoup]:
        """
        Scrape a list of urls and return a list of BeautifulSoup objects.
        """
        if type(urls) is str:
            return await self.fetch(urls)
        logger.debug(f"Fetching {len(urls)} urls, {str(urls)[:100]}...")
        responses = await tqdm_asyncio.gather(*[self.fetch(url) for url in urls])
        # Filter out None or exceptions from the responses
        valid_responses = [response for response in responses if isinstance(response, BeautifulSoup)]
        logger.debug(f"Fetched {len(valid_responses)} valid responses out of {len(urls)}")
        return responses
            
    async def close_session(self) -> None:
        """
        Close the aiohttp session.
        """
        logger.debug("Closing session")
        await self.session.close()
                
    @abstractmethod
    def extract_news_story(self, soup: BeautifulSoup) -> NewsStory:
        """
        Extract the news story from the BeautifulSoup object.
        """
        pass


class BEScraper(BaseScraper):
    """
    Bailiwick Express News Scraper
    """

    REGIONS = ["jsy", "gsy"]
    BASE_URL = "https://www.bailiwickexpress.com/"
    BYLINE_REGEX = re.compile(r"by[- ]?line", re.IGNORECASE) #TODO: does not catch all bylines

    def __init__(self):
        super().__init__()

    def get_page_url(self, region: str, page: int) -> str:
        """
        Create a page url for a given region and page number.
        """
        return f"{self.BASE_URL}{region}/news/?ccm_paging_p={page}"
    
    def get_page_urls(self, region: str, num_pages: int) -> list[str]:
        """
        Create a list of page urls for a given region and number of pages.
        """
        return [self.get_page_url(region, page) for page in range(1, num_pages + 1)]

    def extract_news_story(self, url: str, soup: BeautifulSoup) -> NewsStory:
        """
        Extract the news story from the BeautifulSoup object.
        """
        try:
            div = soup.find("div", class_="news-article") 
            if not div:
                logger.warning("Div not found for url {soup.url}")
                return NewsStory(text="", date="", author="")
            headline = div.find("h1").get_text().strip()
            paragraphs = div.find_all("p")
            joined_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
            byline = div.find("img", src=self.BYLINE_REGEX)
            if byline is not None:
                author = re.sub(self.BYLINE_REGEX, "", byline.get('src')).split('/')[-1].split('.')[0].replace('-', '').replace('_', '').strip().lower()
            else:
                author = ""
            date = soup.find("h4", class_="visible-phone").get_text()
            return NewsStory(headline=headline, text=joined_text, date=date, author=author, url=url)
        except Exception as e:
            logger.exception(e)
            return NewsStory(headline="", text="", date="", author="", url=url)
    
    def get_story_urls(self, soup: BeautifulSoup) -> list[str]:
        """
        Extract news story links from a page of news stories.
        """
        links: list = soup.find_all("a")
        hrefs = [link.get("href") for link in links]
        return list(set([urljoin(self.BASE_URL, href) for href in hrefs if href and re.search(rf"news/[^?]+", href)]))
    
    async def get_all_story_urls(self, region: str, num_pages: int) -> list[str]:
        """
        Get all news story urls for a given region and number of pages.
        """
        page_urls = self.get_page_urls(region, num_pages)
        page_soups = await self.fetch_all(page_urls)
        story_urls = [self.get_story_urls(soup) for soup in page_soups]
        return [url for sublist in story_urls for url in sublist]
    

class JEPScraper(BaseScraper):
    """
    Jersey Evening Post News Scraper
    """
    def __init__(self):
        raise NotImplementedError
    

if __name__ == "__main__":
   
    logging.basicConfig(level=logging.DEBUG)

    async def main():
        scraper = BEScraper()
        urls = await scraper.get_all_story_urls("jsy", 10)
        soups = await scraper.fetch_all(urls)
        breakpoint()
        news_stories = [scraper.extract_news_story(url, soup) for url, soup in zip(urls, soups) if soup]
        breakpoint()

    asyncio.run(main())

