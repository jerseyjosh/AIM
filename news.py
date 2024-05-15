import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class NewsStory:
    def __init__(self, text: str, region: str):
        if not text.endswith("."):
            text += "."
        self.text = text
        self.region = region
    
    def __str__(self):
        return self.text

class NewsScraper:
    def __init__(self):
        self.base_url = "https://www.bailiwickexpress.com/{}/news"
        self.regions = ["jsy", "gsy"]
        self.stories = []
        logger.debug("NewsScraper instance created.")

    def get(self, num_stories=2, n_lines=1):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        logger.debug("WebDriver started in headless mode.")

        # get stories from jsy and gsy
        for region in self.regions:
            url = self.base_url.format(region)
            logger.debug(f"Fetching stories from {url}")
            driver.get(url)
            time.sleep(1)
            links = driver.find_elements(By.XPATH, f"//a[starts-with(@href, '/{region}/news/') and string-length(substring-after(@href, '/{region}/news/')) > 0]")
            hrefs = [link.get_attribute("href") for link in links]
            logger.debug(f"Found {len(hrefs)} links starting with '/{region}/news/'.")
            # iterate stories
            seen_hrefs = set()
            for i in range(len(hrefs)):
                if len(seen_hrefs) >= num_stories:
                    logger.info("Required number of stories fetched.")
                    break
                if hrefs[i] in seen_hrefs:
                    logger.debug(f"Duplicate href skipped: {hrefs[i]}")
                    continue
                logger.debug(f"Navigating to {hrefs[i]}")
                driver.get(hrefs[i])
                time.sleep(1)
                content = driver.find_element(By.CLASS_NAME, 'span8.content')
                text = " ".join(content.text.split('\n')[:n_lines])  # get the first n_lines
                logger.debug(f"Extracted text from {hrefs[i]}: {text[:50]}...")  # logs first 50 characters of the text
                self.stories.append(NewsStory(text, region))
                seen_hrefs.add(hrefs[i])
        
        # quit driver
        driver.quit()
        logger.debug("WebDriver quit.")
        return self.stories

if __name__=="__main__":
    news_scraper = NewsScraper()
    stories = news_scraper.get()
    for story in stories:
        print(story)
