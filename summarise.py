import os
from datetime import date
from utils import save_articles, load_articles
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

nltk.download('punkt')

def summarise(doc, sent_count=5):
  parser = PlaintextParser.from_string(doc, Tokenizer('english'))
  summarizer = LexRankSummarizer()
  summary = summarizer(parser.document, sent_count)
  return " ".join([str(sentence) for sentence in summary])

def summarise_articles(articles):
  summarised_articles = {}  
  for title,text in articles.items():
    summarised_text = summarise(text, sent_count=5)
    summarised_articles[title] = summarised_text
  return summarised_articles

if __name__=='__main__':
  current_date = date.today().strftime('%Y-%m-%d')
  
  raw_articles_path = os.path.join('data', current_date, 'raw_articles.json')
  raw_articles = load_articles(raw_articles_path)
  
  summarised_articles = summarise_articles(raw_articles)
  summarised_articles_path = os.path.join('data', current_date, 'summarised_articles.json')
  save_articles(summarised_articles, summarised_articles_path)