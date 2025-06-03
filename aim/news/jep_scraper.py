""" JEP News Scraper """
# TODO! remove region dependencies as done in BEScraper

import logging

from bs4 import BeautifulSoup
from selenium_driverless import webdriver
from selenium_driverless.types.by import By

from aim.news.models import NewsStory
from aim.news.base_scraper import BaseScraper


logger = logging.getLogger(__name__)

class JEPScraper(BaseScraper):
    """
    Jersey Evening Post News Scraper
    """

    URLS = {
        "jsy": "https://jerseyeveningpost.com/category/news/",
        "jsy_sport": "https://jerseyeveningpost.com/category/sport/",
        "jsy_business": "https://jerseyeveningpost.com/category/business/",
    }

    JEP_COVER = "https://app.jerseyeveningpost.com/t/storefront/magazine"

    def __init__(self):
        super().__init__()
    
    def get_story_urls_from_page(self, soup: BeautifulSoup) -> list[str]:
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
    
    async def get_jep_cover(self) -> str:
        raise NotImplementedError("JEP cover page scraping is not implemented yet.")

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
            image_url = soup.find('figure', class_='post-thumbnail').find('img').get('src')
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
    async def main():
        scraper = JEPScraper()
        html = await scraper.get_jep_cover()
        breakpoint()

    import asyncio
    asyncio.run(main())