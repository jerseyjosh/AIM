import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium_driverless import webdriver
from selenium_driverless.types.by import By
from tenacity import retry

logger = logging.getLogger(__name__)

class GovJeWeather:

    BASE_URL = "https://www.gov.je/weather/"

    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')


    async def get(self) -> BeautifulSoup:
        """
        Get the weather report from the gov.je website.
        """
        async with webdriver.Chrome(options=self.options) as driver:
            # Navigate to the page, wait for initial load
            await driver.get(self.BASE_URL, wait_load=True)

            # wait for specific elements to load
            await driver.find_element(By.CSS_SELECTOR, "table.tide-mobile", timeout=10)
            await driver.find_element(By.CSS_SELECTOR, ".weathergrid", timeout=10)
            await driver.find_element(By.CSS_SELECTOR, "span.boldWeather", timeout=10)
            html = await driver.page_source

        return BeautifulSoup(html, "html.parser")
    
    def to_radio(self, soup: BeautifulSoup) -> str:
        """Parse weather to"""
        tides = self.parse_tides(soup)
        high_tides = [item['time'] for item in tides if item['direction'] == 'high']
        low_tides = [item['time'] for item in tides if item['direction'] == 'low']
        tide_script = f"High tides today at around {', '.join(high_tides)}, with low tides around {', '.join(low_tides)}."
        return f"{self.parse_weather_response(soup)} {tide_script}"
    
    def to_email(self, soup: BeautifulSoup) -> dict:
        """
        News email requires weather to be rendered in jinja template:
            Today's weather: 6°c, few clouds
            Tide: Low 13:14 (1.7m) High 18:51 (10.3m)
            Wednesday 12 February 2025
        """
        # get first temperature for the day
        first_temp = self.parse_temperatures(soup)[0]
        # get short weather summary
        weather_summary = soup.find('div', class_='weathergrid').find('div', class_='borderLeft').text.strip()
        # get tide info
        tides = self.parse_tides(soup)
        first_low_tide = [t for t in tides if t['direction'] == 'low'][0]
        first_high_tide = [t for t in tides if t['direction'] == 'high'][0]
        # format and return
        return {
            'todays_weather': f"{first_temp}, {weather_summary}",
            'tides': f"Low {first_low_tide['time']} ({first_low_tide['height']}) High {first_high_tide['time']} ({first_high_tide['height']})",
            'date': datetime.now().strftime("%A %d %B %Y")
        }
        
    def parse_time(self, time: str) -> str:
        """
        Parse a time string and return a 24-hour time string.
        """
        time_object = datetime.strptime(time, '%H:%M')
        round_minutes = time_object.minute // 15 * 15
        rounded_time = time_object.replace(minute=round_minutes)
        output = rounded_time.strftime("%I:%M%p").lower()
        if output.startswith('0'):
            output = output[1:]
        return output
        
    def replace_force(self, report: str) -> str:
        """
        Replace capital F followed by number with "Force {n}".
        """
        return re.sub(r'F(\d)', r'Force \1', report)
    
    def parse_tides(self, soup: BeautifulSoup):
        tide_rows = soup.find('table', class_='tide-mobile').find_all('tr')
        tides = []
        for row in tide_rows[1:]:
            cols = row.find_all('td')
            tide_entry = {
                'direction': cols[0].text.lower().split()[0],
                'time': self.parse_time(cols[1].text),
                'height': cols[2].text
            }
            tides.append(tide_entry)
        return tides
    
    def parse_temperatures(self, soup: BeautifulSoup):
        temps = soup.find_all('span', class_='boldWeather')
        return [temp.text for temp in temps]
        
    def parse_weather_response(self, soup: BeautifulSoup):
        reports: list[Tag] = soup.find_all('p', class_='description')
        output = ""
        if len(reports) == 0:
            raise ValueError("No weather report found.")
        if len(reports) == 1: # only night
            output += reports[0].text
        elif len(reports) == 2: # afternoon and night.
            output += reports[0].text + " Tonight, " + reports[1].text
        elif len(reports) == 3: # morning, afternoon and night.
            output += reports[0].text + " This afternoon, " + reports[1].text + ". Tonight, " + reports[2].text
        else:
            raise ValueError(f"Too many weather reports found, expected 1-3, got {len(reports)}")
        # try:
        #     output += reports[0].text
        # except IndexError:
        #     logger.error("No weather report found.")
        return self.replace_force(output)
    
if __name__=="__main__":
    async def main():
        weather = GovJeWeather()
        soup = await weather.get()
        email = weather.to_email(soup)
        print(email)
    import asyncio
    asyncio.run(main())