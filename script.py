import openai
from config import OPENAI_KEY, LLM
from utils import load_articles

openai.api_key = OPENAI_KEY


def gpt_translate(text, language):
  response = openai.ChatCompletion.create(
    model=LLM,
    messages=[{
      'role':
      'user',
      'content':
      f'Preserving formatting, translate the following text into {language}: {text}'
    }])
  return response.choices[0].message.content


def gpt_generate(articles):
  titles = '\n'.join([title for title, _ in articles.items()])
  response = openai.ChatCompletion.create(
    model=LLM,
    messages=[{
      "role":
      "system",
      "content":
      "You are an AI news podcast host for the Bailiwick Express. You will receive a list of today's news stories and return a professional and engaging news reading summary, introducing yourself as the Bailiwick Express AI. Respond only with the spoken script."
    }, {
      "role": "user",
      "content": titles
    }])
  news_summary = response.choices[0].message.content
  with open('output.txt', 'w') as f:
    f.write(news_summary)
  return news_summary


if __name__ == "__main__":
  articles = load_articles()
  gpt_generate(articles)
