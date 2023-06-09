import os
import json
from datetime import date

def save_articles(articles, path, override=1):
  # Make sure the directory exists; if it doesn't, create it
  os.makedirs(os.path.dirname(path), exist_ok=True)
  
  if (os.path.exists(path) and override) or not os.path.exists(path):
    with open(path, 'w') as f:
      json.dump(articles, f)
  elif os.path.exists(path) and not override:
    return

def load_articles(path=None):
  if path is None:
    path = os.path.join("./data", date.today().strftime("%Y-%m-%d"), "raw_articles.json")
  with open(path, 'r') as f:
    articles = json.load(f)
  return articles
