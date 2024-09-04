import logging
import re

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

    async def get(self):
        """
        Get the weather for St Helier.
        """
        async with self.driver as driver:
            await driver.get(self.BASE_URL)
            await driver.sleep(1)
            html = await driver.page_source
            return self.parse_weather_response(html)
        
    def replace_force(self, report: str):
        """
        Replace capital F followed by number with "Force {n}".
        """
        return re.sub(r'F(\d)', r'Force \1', report)
        
    def parse_weather_response(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        reports: list[Tag] = soup.find_all('p', class_='description')
        if len(reports) == 1: # only night
            output = reports[0].text
        elif len(reports) == 2: # afternoon and night.
            output = reports[0].text + " Tonight, " + reports[1].text
        elif len(reports) == 3: # morning, afternoon and night.
            output = reports[0].text + " This afternoon, " + reports[1].text + ". Tonight, " + reports[2].text
        else:
            logger.error(f"Unexpected number of reports: {len(reports)}")
            logger.error(reports)
        return self.replace_force(output)
    
if __name__=="__main__":
    async def main():
        weather = GovJeWeather()
        report = await weather.get()
    import asyncio
    asyncio.run(main())