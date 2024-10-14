import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium_driverless import webdriver

logger = logging.getLogger(__name__)

class GovJeWeather:

    BASE_URL = "https://www.gov.je/weather/"

    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=self.options)

    async def close(self):
        """
        Close the driver session.
        """
        await self.driver.close()

    async def get(self) -> str:
        """
        Get the weather report from the gov.je website.
        """
        async with self.driver as driver:
            await driver.get(self.BASE_URL)
            await driver.sleep(5)
            html = await driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            weather = self.parse_weather_response(soup)
            tides = self.get_tides(soup)
            return weather + " " + tides
        
    def parse_time(self, time: str) -> str:
        """
        Parse a time string and return a 24-hour time string.
        """
        time_object = datetime.strptime(time, '%H:%M')
        round_minutes = time_object.minute // 15 * 15
        rounded_time = time_object.replace(minute=round_minutes)
        return rounded_time.strftime("%I:%M%p").lower()
        
    def replace_force(self, report: str) -> str:
        """
        Replace capital F followed by number with "Force {n}".
        """
        return re.sub(r'F(\d)', r'Force \1', report)
    
    def get_tides(self, soup: BeautifulSoup):
        tide_rows = soup.find('table', class_='tide-mobile').find_all('tr')
        high_tides = []
        low_tides = []
        for row in tide_rows[1:]:
            cols = row.find_all('td')
            if 'low' in cols[0].text.lower():
                low_tides.append(self.parse_time(cols[1].text))
            elif 'high' in cols[0].text.lower():
                high_tides.append(self.parse_time(cols[1].text))
        return f"High tides today at around {', '.join(high_tides)}, with low tides around {', '.join(low_tides)}."
        
    def parse_weather_response(self, soup: BeautifulSoup):
        reports: list[Tag] = soup.find_all('p', class_='description')
        output = ""
        # if len(reports) == 1: # only night
        #     output += reports[0].text
        # elif len(reports) == 2: # afternoon and night.
        #     output += reports[0].text + " Tonight, " + reports[1].text
        # elif len(reports) == 3: # morning, afternoon and night.
        #     output += reports[0].text + " This afternoon, " + reports[1].text + ". Tonight, " + reports[2].text
        # else:
        #     logger.error(f"Unexpected number of reports: {len(reports)}")
        #     logger.error(reports)
        try:
            output += reports[0].text
        except IndexError:
            logger.error("No weather report found.")
        return self.replace_force(output)
    
if __name__=="__main__":
    async def main():
        weather = GovJeWeather()
        report = await weather.get()
        breakpoint()
    import asyncio
    asyncio.run(main())