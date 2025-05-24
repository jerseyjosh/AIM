""" JEP News Scraper """
# TODO! remove region dependencies as done in BEScraper

import logging

from bs4 import BeautifulSoup

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