import asyncio
import logging
from argparse import ArgumentParser
from typing import Literal

from news.news_scraper import BEScraper
from news.database import create_news_database, insert_news_stories

logger = logging.getLogger(__name__)

async def scrape_articles(region: Literal['jsy', 'gsy'], num_pages: int):
    """
    Scrape articles from the specified region and number of pages.
    """
    try:
        scraper = BEScraper()
        urls = await scraper.get_all_story_urls(region, num_pages)
        logger.debug(f"Fetched {len(urls)} URLs from region '{region}' and {num_pages} pages.")
        soups = await scraper.fetch_all(urls)
        news_stories = [scraper.extract_news_story(soup) for soup in soups if soup]
        logger.info(f"Extracted {len(news_stories)} news stories.")
        await scraper.close_session()
        return news_stories
    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        return []

def main():
    parser = ArgumentParser()
    parser.add_argument("--region", type=str, default="jsy", help="Region to scrape news from (jsy or gsy)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--log", type=str, default="INFO", help="Logging level")
    args = parser.parse_args()

    # Set logging level
    logging.basicConfig(level=args.log)

    # Scrape and store news articles
    news_stories = asyncio.run(scrape_articles(args.region, args.pages))

    # Create the database and insert the scraped news stories
    db_name = "./news.db"
    create_news_database(db_name)
    insert_news_stories(db_name, news_stories)

    logger.info('Scraping and storing process completed.')

if __name__ == "__main__":
    main()
