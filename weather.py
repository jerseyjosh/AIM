from datetime import datetime
import re

from selenium import webdriver
from selenium.webdriver.common.by import By

class WeatherReport:
    def __init__(self, text: str, date: str):
        self.text = text
        self.date = date

class WeatherScraper:
    def __init__(self):
        self.url = "https://www.gov.je/weather/"
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=self.options)

    # only gets morning report for now
    def get(self):
        # get current date
        date = datetime.now().strftime('%d-%m-%Y')
        # get weather element
        self.driver.get(self.url)
        response = self.driver.find_element(By.XPATH, '//*[@id="simple-tabpanel-0"]/div')
        weather = re.split('Morning|Afternoon|Evening|Night', response.text)
        first_report = weather[0] if len(weather[0]) > 0 else weather[1]
        first_report = ' '.join(first_report.split('\n')[6:]).strip()
        # parse wind speeds
        text = re.sub(r'F(\d)', r'force \1', first_report)
        return WeatherReport(text=text, date=date)
    
    def quit(self):
        self.driver.quit()
    

# if __name__=="__main__":
#     ws = WeatherScraper()
#     report = ws.get()
#     print(report.text)
#     print(report.date)
#     ws.quit()