from datetime import datetime
import re
import logging
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class WeatherReport:
    def __init__(self, text: str, date: str):
        self.text = self._clean_input(text)
        self.date = date

    def _clean_input(self, text):
         # replace F1 with Force 1 etc.
         return re.sub(r'F(\d)', r'force \1', text)

    def __str__(self):
        return f"{self.text}"

class WeatherScraper:
    def __init__(self):
        self.url = "https://www.gov.je/weather/"
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        logger.debug("Initializing WebDriver.")
        self.driver = webdriver.Chrome(options=self.options)

    def get(self):
        date = datetime.now().strftime('%d-%m-%Y')
        logger.info(f"Fetching weather report for {date}")
        self.driver.get(self.url)
        time.sleep(2)
        try:
            response = self.driver.find_element(By.XPATH, '//*[@id="simple-tabpanel-0"]/div')
            weather = re.split('Morning|Afternoon|Evening|Night', response.text)
            first_report = weather[0] if len(weather[0]) > 0 else weather[1]
            first_report = ' '.join(first_report.split('\n')[6:]).strip()
            report = WeatherReport(text=first_report, date=date)
            logger.debug(f"Extracted morning weather report: {str(report)[:100]}...")  # logs first 100 characters
        except Exception as e:
            logger.error("Failed to fetch or parse weather report.", exc_info=True)
            raise
        return report

    def quit(self):
        logger.debug("Closing WebDriver.")
        self.driver.quit()

if __name__=="__main__":
    ws = WeatherScraper()
    try:
        report = ws.get()
        print(report)
    finally:
        ws.quit()
