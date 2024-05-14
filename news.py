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
        self.base_url = "https://www.bailiwickexpress.com/{}/news"
        self.locals = ["jsy", "gsy"]
        self.stories = {"jsy": [], "gsy": []}
        logger.debug("NewsScraper instance created.")

    def get(self, num_stories=2, n_lines=1):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        logger.debug("WebDriver started in headless mode.")

        # get stories from jsy and gsy
        for local in self.locals:
            url = self.base_url.format(local)
            logger.debug(f"Fetching stories from {url}")
            driver.get(url)
            time.sleep(1)
            links = driver.find_elements(By.XPATH, f"//a[starts-with(@href, '/{local}/news/') and string-length(substring-after(@href, '/{local}/news/')) > 0]")
            hrefs = [link.get_attribute("href") for link in links]
            logger.debug(f"Found {len(hrefs)} links starting with '/{local}/news/'.")
            # iterate stories
            seen_hrefs = set()
            for i in range(len(hrefs)):
                if len(self.stories[local]) >= num_stories:
                    logger.info("Required number of stories fetched.")
                    break
                if hrefs[i] in seen_hrefs:
                    logger.debug(f"Duplicate href skipped: {hrefs[i]}")
                    continue
                logger.debug(f"Navigating to {hrefs[i]}")
                driver.get(hrefs[i])
                time.sleep(1)
                content = driver.find_element(By.CLASS_NAME, 'span8.content')
                text = " ".join(content.text.split('\n')[:n_lines])  # get the first 3 lines
                logger.debug(f"Extracted text from {hrefs[i]}: {text[:50]}...")  # logs first 50 characters of the text
                self.stories[local].append(NewsStory(text))
                seen_hrefs.add(hrefs[i])

            # warn if not enough stories found for each local
            if len(self.stories[local]) < num_stories:
                logger.warning(f"Only found {len(self.stories)}/{num_stories} stories.")
                raise Exception(f"Only found {len(self.stories)}/{num_stories}")
        
        # quit driver
        driver.quit()
        logger.debug("WebDriver quit.")
        return self.stories

if __name__=="__main__":
    news_scraper = NewsScraper()
    stories = news_scraper.get()
    breakpoint()
    for story in stories:
        logger.info(story)
