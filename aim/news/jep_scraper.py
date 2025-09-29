""" JEP News Scraper """
# TODO! remove region dependencies as done in BEScraper

import logging
from enum import Enum

from bs4 import BeautifulSoup
from selenium_driverless import webdriver
from selenium_driverless.types.by import By
from tenacity import retry, stop_never, wait_random_exponential, before_sleep_log
from urllib.parse import urljoin


from aim.news.models import NewsStory
from aim.news.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class JEPScraper(BaseScraper):
    """
    Jersey Evening Post News Scraper
    """

    URLS = {
        "jsy_news": "https://jerseyeveningpost.com/category/news/",
        "jsy_sport": "https://jerseyeveningpost.com/category/sport/",
        "jsy_business": "https://jerseyeveningpost.com/category/business/",
        "jsy_premium": "https://jerseyeveningpost.com/tag/premium/"
    }

    class JEPCoverSource(Enum):
        Jep = "https://app.jerseyeveningpost.com/t/storefront/magazine"
        Homelife = "https://app.jerseyeveningpost.com/t/storefront/homelife"
        More = "https://app.jerseyeveningpost.com/t/storefront/more_supplements"

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
    
    async def get_cover(self, source: JEPCoverSource) -> str:
        """
        Launches headless Chrome (selenium_driverless), navigates to JEP_COVER,
        waits for the Bolt iframe to load, then uses a JS snippet to reach inside
        the iframe’s document and return the `data-src` of <img.pp-widget-media__image>.
        This function retries until it succeeds.
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")

        async with webdriver.Chrome(options=options) as driver:
            logger.info("Navigating to JEP cover page...")
            await driver.get(source.value, wait_load=True)

            @retry(
                stop=stop_never,
                wait=wait_random_exponential(multiplier=1, max=10),
                before_sleep=before_sleep_log(logger, logging.INFO),
            )
            async def _get_cover():
                logger.info("Waiting for iframe to appear and load content...")
                # give driver a change
                await driver.sleep(1)
                # verify that <iframe class="content"> exists in the DOM.
                try:
                    await driver.find_element(By.CSS_SELECTOR, "iframe.content", timeout=5)
                except Exception:
                    raise Exception("bolt iframe not yet in DOM")
                # cursed javascript execution
                js = """
                  const frame = document.querySelector("iframe.content");
                  if (!frame || !frame.contentWindow) {
                    return null;
                  }
                  const doc = frame.contentWindow.document;
                  // Look for the <img> with class 'pp-widget-media__image'
                  const img = doc.querySelector("img.pp-widget-media__image");
                  if (!img) {
                    return null;
                  }
                  return img.getAttribute("data-src");
                """
                data_src = await driver.execute_script(js)
                if not data_src:
                    # If no data-src yet, it means either the iframe hasn’t rendered the <img>
                    # or the JS inside the iframe hasn’t inserted it yet. Retry.
                    raise Exception("Image not yet available inside iframe")

                logger.info(f"Found data-src = {data_src}")
                return data_src.split()[0]

            return await _get_cover()

    def parse_story(self, url: str, soup: BeautifulSoup) -> NewsStory:
        """
        Parse a news story from the given url.
        """
        try:
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
            author = soup.find('span', class_='byline').text or "Jersey Evening Post"
            author = author.replace('\n', ' ').strip()
            if author.lower().startswith("by "):
                author = author[3:]
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
        except Exception as e:
            logger.error(f'URL {url} raised error: {e}')
            raise e
        
if __name__ == "__main__":

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('websockets').setLevel(logging.WARNING)

    async def main():
        scraper = JEPScraper()
        soup = await scraper.get_home_page_soup("jsy_premium")
        links = scraper.get_story_urls_from_page(soup)[:5]
        stories = await scraper.fetch_and_parse_stories(links)
        breakpoint()

    import asyncio
    asyncio.run(main())

    
