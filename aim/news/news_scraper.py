from abc import ABC, abstractmethod
from typing import Union, Optional

import os
import logging
import asyncio
import re
from tenacity import retry, wait_random_exponential, stop_never, stop_after_attempt
from contextlib import nullcontext

import aiohttp
from aiohttp_client_cache import CachedSession, SQLiteBackend
from urllib.parse import urljoin
import aiolimiter
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio
from tqdm import tqdm

from aim.news.models import NewsStory

logger = logging.getLogger(__name__)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("aiohttp_client_cache").setLevel(logging.WARNING)

class BaseScraper(ABC):

    def __init__(self, requests_per_period: int = 1000, period_seconds: int = 1): # default 100 requests per second
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        #self.session = CachedSession(cache=SQLiteBackend(cache_name='.cache/aiohttp_cache.sqlite')) # cache does not work, some memory leaks
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None))
        self.limiter = aiolimiter.AsyncLimiter(self.requests_per_period, self.period_seconds) if self.requests_per_period and self.period_seconds else nullcontext()

    def soupify(self, html: str) -> BeautifulSoup:
        """
        Create a BeautifulSoup object from an html string.
        """
        return BeautifulSoup(html, "html.parser")

    @retry(stop=stop_never, wait=wait_random_exponential(multiplier=1, min=1, max=64))
    async def fetch(self, url) -> BeautifulSoup:
        """
        Scrape a url and return the BeautifulSoup object.
        """
        async with self.limiter:
            async with self.session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                return html
 
    async def fetch_all(self, urls: Union[str, list[str]]) -> list[BeautifulSoup]:
        """
        Scrape a list of urls and return a list of BeautifulSoup objects.
        """
        if type(urls) is str:
            return await self.fetch(urls)
        logger.debug(f"Fetching {len(urls)} urls, {str(urls)[:100]}...")
        responses = await tqdm_asyncio.gather(*[self.fetch(url) for url in urls])
        # Filter out None or exceptions from the responses
        valid_responses = [response for response in responses if response]
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
    JSY_URL = "https://www.bailiwickexpress.com/"
    GSY_URL = "https://gsy.bailiwickexpress.com/"

    def __init__(self):
        super().__init__()

    def get_page_url(self, region: str, page: int) -> str:
        """
        Create a page url for a given region and page number.
        """
        if region == "jsy":
            return f"{self.JSY_URL}{region}/news/?ccm_paging_p={page}"
        elif region == "gsy":
            return f"{self.GSY_URL}{region}/news/?ccm_paging_p={page}"
    
    def get_page_urls(self, region: str, num_pages: int) -> list[str]:
        """
        Create a list of page urls for a given region and number of pages.
        """
        logger.debug(f"Getting page urls for {region} for {num_pages} pages")
        return [self.get_page_url(region, page) for page in range(1, num_pages + 1)]

    def extract_news_story(self, url: str, soup: BeautifulSoup) -> NewsStory:
        """
        Extract the news story from the BeautifulSoup object.
        """
        try:
            # get author byline image
            byline = soup.find('div', class_='span8 content').find('img').get('src', '')
            author = byline.split('/')[-1].split('.')[0].lower()
            # get article div
            div = soup.find("div", class_="news-article") 
            if not div:
                logger.warning(f"Div not found for url {soup.url}")
                return NewsStory(text="", date="", author="")
            # get headline
            headline = div.find("h1").get_text().strip()
            # get text
            paragraphs = div.find_all("p")
            joined_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
            # get date
            date = soup.find("h4", class_="visible-phone").get_text()
            return NewsStory(headline=headline, text=joined_text, date=date, author=author, url=url)
        except Exception as e:
            logger.error(e)
            return NewsStory(headline="", text="", date="", author="", url=url)
    
    def get_story_urls(self, region: str, soup: BeautifulSoup, n_stories: Optional[int] = None) -> list[str]:
        """
        Extract news story links from a page of news stories.
        """
        # Get base url based on region
        base_url = self.JSY_URL if region == "jsy" else self.GSY_URL
        # Get article links
        links: list = soup.find_all("a")
        hrefs = [link.get("href") for link in links]
        if not hrefs:
            return []
        article_hrefs = [href for href in hrefs if href and re.search(rf"news/[^?]+", href)]
        unique_hrefs = []
        for href in article_hrefs:
            if href not in unique_hrefs:
                unique_hrefs.append(href)
        full_urls = [urljoin(base_url, href) for href in unique_hrefs]
        return full_urls[:n_stories] if n_stories else full_urls
    
    async def get_all_story_urls(self, region: str, num_pages: int) -> list[str]:
        """
        Get all news story urls for a given region and number of pages.
        """
        page_urls = self.get_page_urls(region, num_pages)
        htmls = await self.fetch_all(page_urls)
        page_soups = [self.soupify(html) for html in htmls if type(html) is str]
        logger.debug(f"Got {len(page_soups)} soups from {num_pages} pages")
        story_urls = [self.get_story_urls(region, soup) for soup in page_soups]
        return [url for sublist in story_urls for url in sublist]
    
    async def get_all_stories_from_n_pages(self, region: str, num_pages: int) -> list[NewsStory]:
        """
        Get news stories from a given region and number of pages.
        """
        logger.debug(f"Getting news stories from {region} for {num_pages} pages")
        urls = await self.get_all_story_urls(region, num_pages)
        htmls = await self.fetch_all(urls)
        soups = []
        for html in tqdm(htmls, desc="Parsing HTML"):
            try:
                soup = self.soupify(html)
            except Exception as e:
                logger.error(f"Error parsing html: {e}")
                soup = None
            soups.append(soup)
        return [self.extract_news_story(url, soup) for url, soup in zip(urls, soups) if soup]
    
class JEPScraper(BaseScraper):
    """
    Jersey Evening Post News Scraper
    """
    def __init__(self):
        raise NotImplementedError
    

if __name__ == "__main__":
   
    logging.basicConfig(level=logging.DEBUG)
    import json

    async def main():
        scraper = BEScraper()
        urls = await scraper.get_all_story_urls("jsy", 1)
        breakpoint()
    
    asyncio.run(main())

