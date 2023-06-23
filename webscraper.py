import argparse
import os
from config import HEADERS, BE_JSY_URL
from selenium import webdriver
from bs4 import BeautifulSoup
import urllib.parse
from datetime import date
from tqdm import tqdm
import json

def scrape_be(url, headers, max_articles, data_dir):
    current_date = date.today().strftime('%Y-%m-%d')
    max_articles = float('inf') if max_articles == 'all' else int(max_articles)

    # get base url
    base_url = urllib.parse.urljoin(url, '/')

    pbar = tqdm(total=max_articles, desc="Articles scraped")
    save_path = os.path.join(data_dir, current_date, 'raw_articles.jsonl')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # If the file already exists, delete it
    if os.path.exists(save_path):
        os.remove(save_path)

    # Set up the browser in headless mode
    options = webdriver.ChromeOptions()
    options.add_argument('-headless')

    # Create a new instance of the Firefox driver
    driver = webdriver.Chrome(options=options)

    while pbar.n < max_articles:
        # Make a request to the website
        try:
            driver.get(url)
        except Exception as err:
            print(f"Error occurred: {err}")
            break

        # Parse the whole HTML page using BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all news boxes
        news_boxes = soup.find_all('div', class_='img-thumb')
        next_button = soup.find('span', {'class': 'ccm-page-right'}).find('a')  # Find the next button

        # Extract the link of each news box
        for i, news_box in enumerate(news_boxes, start=1):
            a_tag = news_box.find_parent('a')

            if a_tag is not None:
                # get relative link from a_tag
                relative_link = a_tag.get('href')

                # get absolute link from base and relative
                absolute_link = urllib.parse.urljoin(base_url, relative_link)

                # Make a new request for each news article page
                try:
                    driver.get(absolute_link)
                except Exception as err:
                    print(f"Error occurred: {err}")
                    continue

                # Parse the article page
                article_soup = BeautifulSoup(driver.page_source, 'html.parser')

                # Extract and print the main text
                headline = article_soup.select('h1')
                paragraphs = article_soup.select('div.content p')
                if paragraphs:
                    article = {headline.text: '\n'.join([p.text for p in paragraphs])}

                    # Write the article directly to the file as a JSON object
                    with open(save_path, 'a') as f:
                        json.dump(article, f)
                        f.write('\n')  # Write each JSON object on a new line

                # Update progress bar
                pbar.update(1)

        # If there's a next button, change the URL to the URL of the next page
        if next_button and pbar.n < max_articles:
            next_link = next_button.get('href')
            url = urllib.parse.urljoin(base_url, next_link)
        else:
            break

    # Close progress bar
    pbar.close()
    # Close the browser
    driver.quit()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Scrape articles from a website.')
    parser.add_argument('-n', '--max-articles', default=100, help='Maximum number of articles to scrape (default: 100). '
                                                                  'Use "all" to scrape until there are no more articles.')

    args = parser.parse_args()
    max_articles = args.max_articles

    scrape_be(url=BE_JSY_URL,
              headers=HEADERS,
              max_articles=max_articles,
              data_dir='./data/')

