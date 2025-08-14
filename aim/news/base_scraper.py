from abc import ABC, abstractmethod
from typing import Union
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
import time

import logging
import asyncio
from tenacity import retry, wait_random_exponential, stop_never, before_sleep_log
from contextlib import nullcontext

import aiohttp
import aiolimiter
from bs4 import BeautifulSoup

from aim.news.models import NewsStory
from aim import HEADERS

logger = logging.getLogger(__name__)


class BaseScraper(ABC):

    # placeholder for urls for each region, will be overwritten by subclass
    URLS = {}

    def __init__(self, requests_per_period: int = 100, period_seconds: int = 1): # default 100 requests per second
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None))
        self.limiter = aiolimiter.AsyncLimiter(self.requests_per_period, self.period_seconds) if self.requests_per_period and self.period_seconds else nullcontext()

    @staticmethod
    def soupify(html: str) -> BeautifulSoup:
        """
        Create a BeautifulSoup object from an html string.
        """
        return BeautifulSoup(html, "html.parser")
    
    def get_regions(self):
        """
        Get the regions available for scraping.
        """
        return list(self.URLS.keys())

    @retry(
            stop=stop_never, 
            wait=wait_random_exponential(multiplier=0.5, max=5),
           before_sleep=before_sleep_log(logger, logging.INFO)
    )
    async def fetch(self, url, headers=None, randomize: bool = True) -> BeautifulSoup:
        """
        Scrape a url and return the BeautifulSoup object.
        """
        if randomize:
            # add a random query to the url to not get a cached result
            u = urlsplit(url)
            q = dict(parse_qsl(u.query, keep_blank_values=True))
            q["_"] = str(int(time.time()*1000))
            url = urlunsplit((u.scheme, u.netloc, u.path, urlencode(q), u.fragment))
        if headers is None:
            headers = HEADERS
        async with self.limiter:
            async with self.session.get(url, headers=headers) as response:
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
        responses = await asyncio.gather(*[self.fetch(url) for url in urls])
        # Filter out None or exceptions from the responses
        valid_responses = [response for response in responses if response]
        logger.debug(f"Fetched {len(valid_responses)} valid responses out of {len(urls)}")
        return responses
            
    async def close(self) -> None:
        """
        Close the aiohttp session.
        """
        logger.debug("Closing session")
        await self.session.close()

    async def get_home_page_soup(self, region: str):
        """Get the home page soup for the given region"""
        assert region.lower() in self.URLS, f"Invalid region {region}"
        return self.soupify(await self.fetch(self.URLS[region]))

    @abstractmethod
    def get_story_urls_from_page(self, soup: BeautifulSoup) -> list[str]:
        """
        Extract the links to all news stories from the current page display.
        """
        pass
    
    @abstractmethod
    def parse_story(self, url: str, soup: BeautifulSoup) -> NewsStory:
        """
        Parse a news story from the given url.
        """
        pass

    async def fetch_and_parse_story(self, url: str) -> NewsStory:
        """
        Fetch and parse a news story from the given url.
        """
        soup = await self.fetch(url)
        return self.parse_story(url, soup)

    async def fetch_and_parse_stories(self, links: list[str]) -> list[BeautifulSoup]:
        """
        Fetch and soupify all news stories from the given list of links.
        """
        responses = await self.fetch_all(links)
        stories = []
        for link,response in zip(links, responses):
            if response:
                soup = self.soupify(response)
                story = self.parse_story(link, soup)
                stories.append(story)
        return stories

    async def get_n_stories_for_region(self, region: str, n: int) -> list[NewsStory]:
        """Get the first n stories for the given region"""
        soup = await self.get_home_page_soup(region)
        links = self.get_story_urls_from_page(soup)[:n]
        stories = await self.fetch_and_parse_stories(links)
        return stories