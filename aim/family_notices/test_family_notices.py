import pytest
from aim.family_notices import FamilyNotices
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_family_notices():
    scraper = FamilyNotices()

    # scrape notices
    notices = await scraper.get_notices()

    assert len(notices) > 0, "No notices found"

    await scraper.close()
