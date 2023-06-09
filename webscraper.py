import os
from config import BE_JSY_URL, HEADERS
import requests
from bs4 import BeautifulSoup
import urllib.parse
from utils import save_articles
from datetime import date
from tqdm import tqdm


def scrape_be(url, headers, max_articles=10):
  articles = {}
  current_date = date.today().strftime('%Y-%m-%d')

  # get base url
  base_url = urllib.parse.urljoin(url, '/')

  pbar = tqdm(total=max_articles, desc="Articles scraped")
  while len(articles) < max_articles:
    # Make a request to the website
    response = requests.get(url=url, headers=headers)
    response.raise_for_status()  # Ensure we got a successful response

    # Parse the whole HTML page using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all news boxes
    news_boxes = soup.find_all('div', class_='img-thumb')
    next_button = soup.find('span', {
      'class': 'ccm-page-right'
    }).find('a')  # Find the next button

    # Extract the link of each news box
    for i, news_box in enumerate(news_boxes, start=1):
      a_tag = news_box.find_parent('a')

      if a_tag is not None:
        # get relative link from a_tag
        relative_link = a_tag.get('href')

        # get absolute link from base and relative
        absolute_link = urllib.parse.urljoin(base_url, relative_link)

        # Make a new request for each news article page
        article_response = requests.get(absolute_link, headers=headers)
        article_response.raise_for_status()

        # Parse the article page
        article_soup = BeautifulSoup(article_response.text, 'html.parser')

        # Extract and print the main text
        paragraphs = article_soup.select('div.content p')
        articles[paragraphs[0].text] = '\n'.join(
          [p.text for p in paragraphs[1:]])

        # Update progress bar
        pbar.update(len(articles) - pbar.n)

    # If there's a next button, change the URL to the URL of the next page
    if next_button and len(articles) < max_articles:
      next_link = next_button.get('href')
      url = urllib.parse.urljoin(base_url, next_link)
    else:
      break

  # Close progress bar
  pbar.close()

  return articles, current_date


if __name__ == "__main__":

  DATA_DIR = os.path.join(os.getcwd(), 'data')
  articles, current_date = scrape_be(url=BE_JSY_URL,
                                     headers=HEADERS,
                                     max_articles=100)

  save_path = os.path.join(DATA_DIR, current_date, 'raw_articles.json')
  save_articles(articles=articles, path=save_path)
