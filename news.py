import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

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
        logger.debug("NewsScraper instance created.")

    def get(self, num_stories=2, n_lines=3):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        logger.debug("WebDriver started in headless mode.")
        driver.get(self.url)
        time.sleep(2)
        logger.info(f"Accessing website at {self.url}")
        
        links = driver.find_elements(By.XPATH, "//a[starts-with(@href, '/jsy/news/') and string-length(substring-after(@href, '/jsy/news/')) > 0]")
        hrefs = [link.get_attribute("href") for link in links]
        logger.debug(f"Found {len(hrefs)} links starting with '/jsy/news/'.")
        
        seen_hrefs = set()
        for i in range(len(hrefs)):
            if len(self.stories) >= num_stories:
                logger.info("Required number of stories fetched.")
                break
            if hrefs[i] in seen_hrefs:
                logger.debug(f"Duplicate href skipped: {hrefs[i]}")
                continue
            logger.debug(f"Navigating to {hrefs[i]}")
            driver.get(hrefs[i])
            time.sleep(2)
            content = driver.find_element(By.CLASS_NAME, 'span8.content')
            text = " ".join(content.text.split('\n')[:n_lines])  # get the first 3 lines
            logger.debug(f"Extracted text from {hrefs[i]}: {text[:50]}...")  # logs first 50 characters of the text
            self.stories.append(NewsStory(text))
            seen_hrefs.add(hrefs[i])
        
        if len(self.stories) < num_stories:
            logger.warning(f"Only found {len(self.stories)}/{num_stories} stories.")
            raise Exception(f"Only found {len(self.stories)}/{num_stories}")
        
        driver.quit()
        logger.debug("WebDriver quit.")
        return self.stories

if __name__=="__main__":
    news_scraper = NewsScraper()
    stories = news_scraper.get()
    for story in stories:
        logger.info(story)
