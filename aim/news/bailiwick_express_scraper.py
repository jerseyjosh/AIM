""" Bailiwick Express News Scraper """

import logging
import asyncio
import re
from tenacity import retry, wait_random_exponential, stop_never, before_sleep_log

from bs4 import BeautifulSoup
from selenium_driverless import webdriver
from selenium_driverless.types.by import By

from urllib.parse import urljoin

from aim.news.models import NewsStory
from aim.news.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class BEScraper(BaseScraper):
    """
    Bailiwick Express News Scraper
    """

    URLS = {
        "jsy": "https://www.bailiwickexpress.com/news",
        "gsy": "https://www.bailiwickexpress.com/bailiwickexpress-guernsey-edition/",
        "jsy_business": "https://www.bailiwickexpress.com/jsy-business/",
        "gsy_business": "https://www.bailiwickexpress.com/gsy-business/",
        "jsy_sport": "https://www.bailiwickexpress.com/jsy-sport/",
        "gsy_sport": "https://www.bailiwickexpress.com/gsy-sport/",
        "jsy_community": "https://www.bailiwickexpress.com/jsy-community/",
        "jsy_podcasts": "https://www.bailiwickexpress.com/jsy-radio-podcasts/"
    }

    CONNECT_COVER = "https://www.bailiwickexpress.com/jsy-connect/"

    def __init__(self):
        super().__init__()
    
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

    def get_story_urls_from_page(self, soup: BeautifulSoup) -> list[str]:
        """
        Extract the links to all news stories from the current page display.
        """
        articles = soup.find_all("article", attrs={"data-post-id": True})
        news_urls = []
        seen = set()
        for article in articles:
            link = article.find('a').get('href')
            if link and link not in seen:
                news_urls.append(link)
                seen.add(link)
        return news_urls
    
    async def get_connect_cover(self) -> str:
        """Get connect cover image link, have to use hacky chromedriver solution for iframe rendering."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')  # Required for some cloud environments
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        options.add_argument('--disable-gpu')  # Often needed in headless environments
        
        async with webdriver.Chrome(options=options) as driver:
            # Initial page load with very generous timeout
            logger.info("Starting to load connect cover page...")
            await driver.get(self.CONNECT_COVER, wait_load=True)
            
            @retry(
                stop=stop_never, 
                wait=wait_random_exponential(multiplier=1, max=10),  # Increased wait times
                before_sleep=before_sleep_log(logger, logging.INFO)
            )
            async def _get_cover():
                logger.info("Attempting to find iframe...")
                
                # Wait longer before looking for iframe
                await driver.sleep(1)  # Give more time for JS to load
                
                try:
                    # Try different iframe selectors
                    for selector in ['iframe', 'iframe[id*="issuu"]', 'iframe[src*="issuu"]']:
                        try:
                            logger.info(f"Trying to find iframe with selector: {selector}")
                            iframe = await driver.find_element(By.CSS_SELECTOR, selector, timeout=15)
                            if iframe:
                                logger.info("Found iframe!")
                                break
                        except Exception as e:
                            logger.warning(f"Selector {selector} failed: {str(e)}")
                    else:
                        raise Exception("No iframe found with any selector")
                    
                    logger.info("Switching to iframe...")
                    await driver.switch_to.frame(iframe)
                    
                    logger.info("Looking for side-image...")
                    await driver.find_element(By.CLASS_NAME, 'side-image', timeout=15)
                    
                    logger.info("Getting page source...")
                    html = await driver.page_source
                    current_page_url = await driver.current_url
                    
                    # Process results
                    logger.info("Processing HTML...")
                    soup = self.soupify(html)
                    side_image = soup.find('div', class_='side-image')
                    if not side_image or not side_image.img:
                        raise Exception("Side image element not found in HTML")
                    
                    relative_path = side_image.img.get('src')
                    if not relative_path:
                        raise Exception("No src attribute found in image")
                    
                    return urljoin(current_page_url, relative_path)
                    
                except Exception as e:
                    logger.error(f"Error in _get_cover: {str(e)}")
                    # Log the page source for debugging
                    try:
                        page_source = await driver.page_source
                        logger.debug(f"Current page source: {page_source[:500]}...")
                    except:
                        logger.error("Could not get page source for debugging")
                    raise
                
            return await _get_cover()
        
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
        author = soup.find('a', class_=['url', 'fn', 'a'])
        if author is not None:
            author = author.text.strip()
        else:
            author = "Bailiwick Express"
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
    
if __name__ == "__main__":

    async def main():
        scraper = BEScraper()
        stories = await scraper.get_n_stories_for_region('jsy_podcasts', 5)
        breakpoint()

    asyncio.run(main())
