import pytest
import asyncio
import uvloop
import imghdr
from io import BytesIO
import aiohttp

from aim.news import BEScraper, JEPScraper
from aim.news.models import NewsStory
from aim import HEADERS

# Use uvloop for faster asyncio
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

@pytest.mark.asyncio
async def test_be_scraper():
    scraper = BEScraper()
    regions = scraper.get_regions()
    assert len(regions) > 0, "No regions found"

    # get stories
    stories = await asyncio.gather(*(scraper.get_n_stories_for_region(region, 5) for region in regions))
    await scraper.close()

    # convert to dict
    result = dict(zip(regions, stories))

    assert len(result) > 0, "No stories found"
    assert all(len(stories) == 5 for stories in result.values()), "Not all regions have 5 stories"
    assert all(isinstance(story, NewsStory) for stories in result.values() for story in stories), "Not all stories are NewsStory instances"

@pytest.mark.asyncio
async def test_connect_cover():
    # get cover url
    scraper = BEScraper()
    connect = await scraper.get_connect_cover("jsy")
    await scraper.close()
    # try download and check if image
    async with aiohttp.ClientSession() as session:
        async with session.get(connect, headers=HEADERS) as image:
            assert image.status == 200, "Could not download image"
            img_type = imghdr.what(BytesIO(await image.read()))
            print(f"Image type: {img_type}")  # This will only be visible with `-s`
            assert img_type is not None, "Not an image"

@pytest.mark.asyncio
async def test_jep_scraper():
    scraper = JEPScraper()
    regions = scraper.get_regions()
    assert len(regions) > 0, "No regions found"

    # get stories
    stories = await asyncio.gather(*(scraper.get_n_stories_for_region(region, 5) for region in regions))
    await scraper.close()

    # convert to dict
    result = dict(zip(regions, stories))

    assert len(result) > 0, "No stories found"
    assert all(len(stories) == 5 for stories in result.values()), "Not all regions have 5 stories"
    assert all(isinstance(story, NewsStory) for stories in result.values() for story in stories), "Not all stories are NewsStory instances"
