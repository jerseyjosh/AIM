import logging
import re

from bs4 import BeautifulSoup
from selenium_driverless import webdriver

logger = logging.getLogger(__name__)

class GovJeWeather:

    BASE_URL = "https://www.gov.je/weather/"

    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=self.options)

    async def get(self):
        """
        Get the weather for St Helier.
        """
        async with self.driver as driver:
            await driver.get(self.BASE_URL)
            await driver.sleep(2)
            html = await driver.page_source
            return self.parse_weather_response(html)
        
    def parse_weather_response(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        report = soup.find('p', class_='description').text
        # replace capital F followed by number with "Force {n}"
        report = re.sub(r'F(\d)', r'Force \1', report)
        return report