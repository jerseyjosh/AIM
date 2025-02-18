import pytest

from aim.news.models import NewsStory
from aim.news.news_scraper import BEScraper 

@pytest.mark.asyncio
async def test_home_page_soup_jsy():
    scraper = BEScraper()
    soup = await scraper.get_home_page_soup("jsy")
    assert soup is not None, "Failed to get homepage soup for jsy"
    # Basic sanity check for presence of <html> or <body>
    assert soup.find("html") is not None, "Soup does not contain <html> tag"
    await scraper.close()

@pytest.mark.asyncio
async def test_home_page_soup_gsy():
    scraper = BEScraper()
    soup = await scraper.get_home_page_soup("gsy")
    assert soup is not None, "Failed to get homepage soup for gsy"
    # Basic sanity check
    assert soup.find("html") is not None, "Soup does not contain <html> tag"
    await scraper.close()

@pytest.mark.asyncio
async def test_get_n_stories_for_region_jsy():
    scraper = BEScraper()
    # Attempt to get 3 stories
    stories = await scraper.get_n_stories_for_region("jsy", 3)
    await scraper.close()

    assert len(stories) <= 3, "Returned more stories than requested"
    for story in stories:
        assert isinstance(story, NewsStory), "Expected a NewsStory object"
        assert story.headline, "Expected a headline"
        assert story.text, "Expected text content"
        assert story.url, "Expected a URL"

@pytest.mark.asyncio
async def test_get_podcast_stories():
    scraper = BEScraper()
    # Attempt to get 2 stories for each region
    results = await scraper.get_podcast_stories(2)
    await scraper.close()

    assert len(results) == 2, "Expected two elements [jsy_stories, gsy_stories]"
    jsy_stories, gsy_stories = results
    for region_stories in (jsy_stories, gsy_stories):
        for story in region_stories:
            assert isinstance(story, NewsStory), "Expected a NewsStory object"
            assert story.headline, "Expected a headline"
            assert story.text, "Expected text content"
            assert story.url, "Expected a URL"
