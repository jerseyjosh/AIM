from abc import ABC, abstractmethod
from typing import Union, Optional

import os
import logging
import asyncio
import re
from tenacity import retry, wait_random_exponential, stop_never, stop_after_attempt
from contextlib import nullcontext

import aiohttp
from urllib.parse import urljoin
import aiolimiter
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio
from tqdm import tqdm

from aim.news.models import NewsStory

logger = logging.getLogger(__name__)


class BaseScraper(ABC):

    def __init__(self, requests_per_period: int = 100, period_seconds: int = 1): # default 100 requests per second
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        #self.session = CachedSession(cache=SQLiteBackend(cache_name='.cache/aiohttp_cache.sqlite')) # cache does not work, some memory leaks
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None))
        self.limiter = aiolimiter.AsyncLimiter(self.requests_per_period, self.period_seconds) if self.requests_per_period and self.period_seconds else nullcontext()

    @staticmethod
    def soupify(html: str) -> BeautifulSoup:
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
            
    async def close(self) -> None:
        """
        Close the aiohttp session.
        """
        logger.debug("Closing session")
        await self.session.close()


class BEScraper(BaseScraper):
    """
    Bailiwick Express News Scraper
    """

    REGIONS = ["jsy", "gsy"]
    JSY_URL = "https://www.bailiwickexpress.com/"
    GSY_URL = "https://www.bailiwickexpress.com/bailiwickexpress-guernsey-edition/"

    def __init__(self):
        super().__init__()

    async def get_home_page_soup(self, region: str):
        assert region.lower() in ['jsy', 'gsy'], "Region must be one of jsy, gsy"
        if region.lower() == 'jsy':
            url = self.JSY_URL
        elif region.lower() == 'gsy':
            url = self.GSY_URL
        return self.soupify(await self.fetch(url))
    
    async def get_podcast_stories(self, n_stories_per_region: int) -> tuple[list[NewsStory], list[NewsStory]]:
        """Get first n stories for each region for daily news podcast"""
        # return home pages concurrently
        jsy_soup, gsy_soup = await asyncio.gather(
            self.get_home_page_soup('jsy'),
            self.get_home_page_soup('gsy')
        )
        # parse for story urls
        jsy_links = self.get_story_urls_from_page(jsy_soup, 'jsy')[:n_stories_per_region]
        gsy_links = self.get_story_urls_from_page(gsy_soup, 'gsy')[:n_stories_per_region]
        jsy_stories, gsy_stories = await asyncio.gather(
            self.fetch_and_parse_stories(jsy_links),
            self.fetch_and_parse_stories(gsy_links)
        )
        return jsy_stories, gsy_stories

    def get_story_urls_from_page(self, soup: BeautifulSoup, region: str) -> list[str]:
        """
        Extract the links to all news stories from the current page display.
        """
        links = soup.find_all('a')
        news_urls = []
        seen = set() # keep track of seen to maintain order without duplicates
        pattern = r'/news/.+' if region == 'jsy' else r'/news-ge/.+'
        for link in links:
            href = link.get('href')
            if href and re.search(pattern, href) and href not in seen:
                news_urls.append(href)
                seen.add(href)
        return news_urls
    
    async def fetch_and_soupify_story(self, url: str) -> BeautifulSoup:
        """
        Fetch and soupify a news story from the given url.
        """
        return self.soupify(await self.fetch(url))
    
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
        links = self.get_story_urls_from_page(soup, region)[:n]
        stories = await self.fetch_and_parse_stories(links)
        return stories
        
    def parse_story(self, url, soup: BeautifulSoup) -> NewsStory:
        """
        Parse a news story from the given url.
        """
        # get headline
        headline = soup.find('h1').text.strip()
        # get article text
        entry_content = soup.find('div', class_='entry-content')
        p_tags = entry_content.find_all('p')
        text = '\n'.join([p.text.strip() for p in p_tags])
        # get date
        date = soup.find('time').text
        # get author
        author = soup.find('a', class_=['url', 'fn', 'a']).text
        # get image url
        image_url = soup.find('figure', class_='post-thumbnail').find('img').get('src')
        return NewsStory(
            headline=headline,
            text=text,
            date=date,
            author=author,
            url=url,
            image_url=image_url
        )

if __name__ == "__main__":
   
    logging.basicConfig(level=logging.DEBUG)
    import json

    async def main():
        scraper = BEScraper()
        stories = await scraper.get_n_stories_for_region('jsy', 5)
        breakpoint()
    
    asyncio.run(main())

