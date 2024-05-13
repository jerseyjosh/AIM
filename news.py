from selenium import webdriver
from selenium.webdriver.common.by import By

class NewsStory:
    def __init__(self, text):
        if not text.endswith("."):
            text += "."
        self.text = text
    
    def __str__(self):
        return self.text

class NewsScraper:
    def __init__(self):
        self.url = "https://www.bailiwickexpress.com/jsy/news/"
        self.stories = []
    
    def get(self):
        raise NotImplementedError("NewsScraper not done yet.")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.get(self.url)
        #stories = driver.find_elements(By.XPATH, #TODO)