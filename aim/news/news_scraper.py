from abc import ABC, abstractmethod
from typing import Union

import logging
import asyncio
import re
from tenacity import retry, wait_random_exponential, stop_never, before_sleep_log
from contextlib import nullcontext

import aiohttp
import aiolimiter
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio
from selenium_driverless import webdriver
from selenium_driverless.types.by import By

from urllib.parse import urljoin

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
    async def fetch(self, url) -> BeautifulSoup:
        """
        Scrape a url and return the BeautifulSoup object.
        """
        async with self.limiter:
            async with self.session.get(url, headers=HEADERS) as response:
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

    async def get_home_page_soup(self, region: str):
        """Get the home page soup for the given region"""
        assert region.lower() in self.URLS, f"Invalid region {region}"
        return self.soupify(await self.fetch(self.URLS[region]))

    @abstractmethod
    def get_news_pattern(self, region: str) -> str:
        """
        Get the regex pattern for news urls for the given region.
        """
        pass

    @abstractmethod
    def get_story_urls_from_page(self, soup: BeautifulSoup, region: str) -> list[str]:
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


class BEScraper(BaseScraper):
    """
    Bailiwick Express News Scraper
    """

    URLS = {
        "jsy": "https://www.bailiwickexpress.com/",
        "gsy": "https://www.bailiwickexpress.com/bailiwickexpress-guernsey-edition/",
        "jsy_business": "https://www.bailiwickexpress.com/jsy-business/",
        "gsy_business": "https://www.bailiwickexpress.com/gsy-business/",
        "jsy_sport": "https://www.bailiwickexpress.com/jsy-sport/",
        "gsy_sport": "https://www.bailiwickexpress.com/gsy-sport/",
    }

    CONNECT_COVER = "https://www.bailiwickexpress.com/jsy-connect/"

    def __init__(self):
        super().__init__()

    def get_news_pattern(self, region: str):
        """
        Get the regex pattern for news urls for the given region.
        """
        region = region.lower()
        if region == "jsy":
            return r'/news/.+'
        elif region == "gsy":
            return r'/news-ge/.+'
        elif region == "jsy_business":
            return r'/business/.+'
        elif region == "gsy_business":
            return r'/business-ge/.+'
        elif region == "jsy_sport":
            return r'/sport/.+'
        elif region == "gsy_sport":
            return r'/sport-ge/.+'
        else:
            raise NotImplementedError(f"Invalid region {region}")
    
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
        # fetch and parse stories concurrently
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
        pattern = self.get_news_pattern(region)
        for link in links:
            href = link.get('href')
            if href and re.search(pattern, href) and href not in seen:
                news_urls.append(href)
                seen.add(href)
        return news_urls
    
    async def get_connect_cover(self) -> NewsStory:
        """Get connect cover image link, have to use hacky chromedriver solution for iframe rendering."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new') # headless mode with new session
        async with webdriver.Chrome(options=options) as driver:
            await driver.get(self.CONNECT_COVER, wait_load=True)
            await driver.sleep(1)
            iframe = await driver.find_element(By.CSS_SELECTOR, 'iframe')
            await driver.switch_to.frame(iframe) # causes warning
            await driver.find_element(By.CLASS_NAME, 'side-image')
            html = await driver.page_source
            current_page_url = await driver.current_url
        # soupify
        soup = self.soupify(html)
        # get img src
        relative_path = soup.find('div', class_='side-image').img.get('src')
        return urljoin(current_page_url, relative_path)
        
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
        try:
            image_url = soup.find('figure', class_='post-thumbnail').find('img').get('src')
            image_url = image_url.split('?')[0] # remove query string
        except Exception as e:
            logger.debug(f"Failed to get image url for {url}")
            image_url = None
        return NewsStory(
            headline=headline,
            text=text,
            date=date,
            author=author,
            url=url,
            image_url=image_url
        )
    
class JEPScraper(BaseScraper):
    """
    Jersey Evening Post News Scraper
    """

    URLS = {
        "jsy": "https://jerseyeveningpost.com/category/news/",
        "jsy_sport": "https://jerseyeveningpost.com/category/sport/",
        "jsy_business": "https://jerseyeveningpost.com/category/business/",
    }

    def __init__(self):
        super().__init__()

    def get_news_pattern(self, region: str):
        """
        Get the regex pattern for news urls for the given region.
        """
        region = region.lower()
        if region == "jsy":
            return r'/news/.+'
        elif region == "jsy_business":
            return r'/business/.+'
        elif region == "jsy_sport":
            return r'/sport/.+'
        else:
            raise ValueError(f"Invalid region {region}")
    
    def get_story_urls_from_page(self, soup: BeautifulSoup, region: str) -> list[str]:
        """
        Extract the links to all news stories from the current page display.
        """
        titles = soup.find_all('h2', class_='entry-title')
        news_urls = []
        for title in titles:
            link = title.find('a').get('href')
            if link:
                news_urls.append(link)
        return news_urls
    
    def parse_story(self, url: str, soup: BeautifulSoup) -> NewsStory:
        """
        Parse a news story from the given url.
        """
        # get headline
        headline = soup.find('h1', class_='entry-title').text.strip()
        # get article text
        entry_content = soup.find('div', class_='entry-content')
        p_tags = entry_content.find_all('p')
        text = '\n'.join([p.text.strip() for p in p_tags])
        # capitalize first word of text, JEP defaults to all caps first word
        words = text.split()
        if words[0].lower() == 'a':
            words[0] = words[0].capitalize()
            words[1] = words[1].lower()
        else:
            words[0] = words[0].capitalize()
        text = ' '.join(words)
        # get date
        date = soup.find('time').text
        # get author
        author = soup.find('span', class_='author').text
        # get image url
        try:
            image_url = soup.find('figure', class_='wp-block-image').find('img').get('src')
        except Exception as e:
            logger.debug(f"Failed to get image url for {url}")
            image_url = None
        return NewsStory(
            headline=headline,
            text=text,
            date=date,
            author=author,
            url=url,
            image_url=image_url
        )

if __name__ == "__main__":
   
    #logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('websockets').setLevel(logging.ERROR)

    async def main():
        scraper = BEScraper()
        connect = await scraper.get_connect_cover()
        breakpoint()
    asyncio.run(main())

