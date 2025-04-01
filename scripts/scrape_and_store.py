import asyncio
import logging
from argparse import ArgumentParser
from typing import Literal

from news.news_scraper import BEScraper
from news.database import create_news_database, insert_news_stories

logger = logging.getLogger(__name__)

async def main():
    parser = ArgumentParser()
    parser.add_argument("--region", type=str, default="jsy", help="Region to scrape news from (jsy or gsy)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--log", type=str, default="DEBUG", help="Logging level")
    args = parser.parse_args()

    # Set logging level
    logging.basicConfig(level=args.log)

    # Scrape and store news articles
    scraper = BEScraper()
    news_stories = await scraper.get_all_stories_from_n_pages(args.region, args.pages)
    await scraper.close_session()

    # Create the database and insert the scraped news stories
    db_name = "./news.db"
    create_news_database(db_name)
    insert_news_stories(db_name, news_stories)

    logger.info('Scraping and storing process completed.')

if __name__ == "__main__":
    import uvloop
    uvloop.run(main())
