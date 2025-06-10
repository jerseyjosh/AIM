import aiohttp
import aiolimiter
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dataclasses import dataclass
import re
from typing import Optional

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://familynotices.jerseyeveningpost.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133")',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

BASE_URL = "https://familynotices.jerseyeveningpost.com/wp-admin/admin-ajax.php"

@dataclass
class FamilyNotice:

    name: str
    url: str
    funeral_director: str
    additional_text: str = ''

    def __post_init__(self):
        self.name = self.format_name(self.name)
        self.url = self.url.strip()

    def __str__(self):
        return self.name
    
    @staticmethod
    def format_name(name: str) -> str:
        """
        Formats a name from 'Last, First (Extra1) (Extra2)' to 'First Last (Extra1) (Extra2)'.
        Handles multiple parenthetical parts.
        """
        # Extract all bracketed parts
        bracketed_parts = re.findall(r"\(.*?\)", name)
        
        # Remove bracketed parts from the main name
        name_without_brackets = re.sub(r"\(.*?\)", "", name).strip()
        
        # Handle "Last, First" format
        if "," in name_without_brackets:
            last, first = [part.strip() for part in name_without_brackets.split(",", 1)]
            formatted_name = f"{first} {last}"
        else:
            formatted_name = name_without_brackets  # If no comma, assume already correct

        # Append all extracted bracketed parts at the end
        if bracketed_parts:
            formatted_name = f"{formatted_name} {' '.join(bracketed_parts)}"

        # Capitalize first letter of each word, except for 'née'
        return formatted_name.title().replace('Née', 'née')

# Asynchronous Scraper Class
class FamilyNotices:
    def __init__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None))
        self.limiter = aiolimiter.AsyncLimiter(100, 1)

    async def fetch(self, url, params):
        """Fetch data with provided parameters."""
        async with self.limiter:
            async with self.session.get(url, headers=HEADERS, params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def close(self):
        await self.session.close()
        
    async def get_notices(self, start_date: datetime = None, end_date: datetime = None) -> list[FamilyNotice]:
        """Fetch notices for a given date range (YYYY-MM-DD format)."""
        # default to today if not provided
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        start_date = start_date or (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y-%m-%d")
        # php request params
        params = {
            "action": "alm_get_posts",
            "query_type": "standard",
            "id": "alm_search",
            "post_id": "0",
            "slug": "home",
            "canonical_url": "https://familynotices.jerseyeveningpost.com/",
            "posts_per_page": "40",
            "page": "0",
            "offset": "0",
            "post_type": "notice",
            "repeater": "default",
            "seo_start_page": "1",
            "filters": "true",
            "filters_startpage": "0",
            "filters_target": "search",
            "facets": "false",
            "theme_repeater": "notice-card.php",
            "taxonomy": "notice-category",
            "taxonomy_terms": "in-sympathy",
            "taxonomy_operator": "IN",
            "taxonomy_include_children": "true",
            "day": f"{start_date} to {end_date}",
            "order": "DESC",
            "orderby": "date",
        }
        # fetch data
        response_data = await self.fetch(BASE_URL, params)
        # parse html response
        soup = BeautifulSoup(response_data["html"], "html.parser")
        # return parsed notices
        notices = self.parse_notices(soup)
        return notices
    
    def parse_notices(self, soup: BeautifulSoup) -> list[FamilyNotice]:
        """Parse notices from the BeautifulSoup object."""
        notices = []
        seen = set()
        for notice in soup.find_all("div", class_="notice-card"):
            name = notice.find('h3').text
            if name in seen:
                continue
            seen.add(name)
            url = notice.find('a').get('href')
            # get funeral director
            text = notice.text
            funeral_director = ''
            if 'Pitcher & Le Quesne' in text:
                funeral_director = 'Pitcher & Le Quesne Funeral Directors'
            elif 'Maillards' in text and 'maillard' not in name.lower():
                funeral_director = 'Maillards Funeral Directors'
            elif "De Gruchy's Funeral" in text and 'de gruchy' not in name.lower():
                funeral_director = "De Gruchy's Funeral Care"
            notices.append(FamilyNotice(name=name, url=url, funeral_director=funeral_director))
        return notices
    

if __name__ == "__main__":

    async def main():
        scraper = FamilyNotices()
        results = await scraper.get_notices(
            datetime(2025,6,1),
            datetime(2025,6,10)
        )

    asyncio.run(main())

