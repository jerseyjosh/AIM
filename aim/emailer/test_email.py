import asyncio
import os
import pickle

from aim.news.news_scraper import BEScraper
from aim.emailer import Email

DIR = os.path.dirname(__file__)

async def get_test_stories(cache_path = './test_stories.pkl'):
    full_cache = os.path.join(os.path.dirname(__file__), cache_path)
    if os.path.exists(full_cache):
        with open(full_cache, 'rb') as f:
            return pickle.load(f)
    scraper = BEScraper()
    jsy_stories, gsy_stories = await scraper.get_podcast_stories(7)
    stories = jsy_stories + gsy_stories
    with open(full_cache, 'wb') as f:
        pickle.dump(stories, f)
    return stories

def make_test_email():
    stories = asyncio.run(get_test_stories())
    email = Email('be_template.html')
    save_path = os.path.join(DIR, 'test_email.html')
    top_image_url = "https://i1.createsend1.com/ei/d/D1/8C6/E5E/221251/csfinal/jsyemailheader10.02.25.jpg"
    email.render(save_path=save_path, news_stories=stories, top_image_url=top_image_url)

if __name__ == "__main__":
    make_test_email()