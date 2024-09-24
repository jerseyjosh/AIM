import asyncio
from dotenv import load_dotenv, find_dotenv
import os
import logging
load_dotenv(find_dotenv())

import pandas as pd
from tqdm.auto import tqdm

from openai import OpenAI
import tiktoken
import sqlite3

from aim.news.models import NewsStory

logger = logging.getLogger(__name__)
logging.getLogger('httpx').setLevel(logging.WARNING)

SUMMARY_PROMPT = """
    Convert this news article into a set of shorthand bullet pointed notes that the author would have used to create it.
    Use the most succinct amount of information but do not miss out any details.
"""
SUMMARY_MODEL = "gpt-4o-mini"
TOKEN_LIMIT = 5000
WORD_LIMIT = 1600 # 99% of stories are below 1600 words
N_SAMPLES = 10 # number of samples per word count strata

def get_openai_client(openai_key: str) -> OpenAI:
    return OpenAI(api_key=openai_key)

def get_news_stories(db_path: str) -> NewsStory:
    """
    Fetch news stories from the database.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM news_stories", conn).set_index('id')
    return df

def process_stories(stories: pd.DataFrame) -> pd.DataFrame:
    """
    Add features to news stories dataframe.
    """
    # create full article from headline and text
    stories['full_article'] = stories.apply(lambda x: f"<headline>{x['headline'].strip()}</headline>\n<text>{x['text'].strip()}</text>", axis=1)
    # get n_tokens
    stories['n_tokens'] = stories['full_article'].apply(get_tokens)
    # filter stories with too many tokens
    stories = stories[stories['n_tokens'] < TOKEN_LIMIT]   
    # get word counts
    stories['n_words'] = stories['text'].apply(lambda x: len(x.split()))
    stories = stories[stories['n_words'] < WORD_LIMIT] # ignore outliers
    stories['n_words_round_100'] = stories['n_words'].apply(lambda x: round(x, -2))
    stories['n_words_round_100'].replace(0, '<100', inplace=True)
    # get rid of focus, gallery, play pieces etc.
    first_words = stories['headline'].apply(lambda x: x.split()[0])
    stories = stories[~first_words.str.endswith(":")]
    # get rid of ART FIX
    stories = stories[~stories['headline'].str.contains("ART FIX")]
    return stories

def stratified_sample(stories: pd.DataFrame, n_samples: int) -> pd.DataFrame:
    """
    Get sample of news stories stratified by n_words_round_100.
    """
    return stories.groupby('n_words_round_100').apply(lambda x: x.sample(min(n_samples, len(x)))).reset_index(drop=True)

def get_tokens(input: str, model: str = SUMMARY_MODEL) -> int:
    """
    Get number of tokens for a given model in a string
    """
    return len(tiktoken.encoding_for_model(model).encode(input))

def get_news_notes(client: OpenAI, story_text: str) -> str:
    """
    Summarise news story into a set of facts.
    """
    # check tokens
    tokens = get_tokens(story_text)
    if tokens > 4000:
        logger.warning(f"Story too long: {tokens} tokens, skipping")
        return None
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": story_text.strip()},
        ],
        model="gpt-4o-mini"
    )
    return response.choices[0].message.content

def main():

    logging.basicConfig(level=logging.INFO)

    # get news stories sample
    logger.info("Getting news stories")
    stories = get_news_stories(db_path = '../../news.db')
    stories = process_stories(stories)
    stories = stratified_sample(stories, N_SAMPLES)

    # get story notes
    logger.info("Getting story notes")
    openai_key = os.getenv('OPENAI_KEY')
    client = get_openai_client(openai_key)
    notes = []
    for i in tqdm(range(len(stories))):
        story = stories.iloc[i]['full_article']
        story_notes = get_news_notes(client, story)
        logger.debug(f"Story: {story[:100]}, Notes: {story_notes[:100]}")
        notes.append(story_notes)
    stories['gpt_notes'] = notes
    stories.to_csv('finetuning_data.csv')

if __name__ == "__main__":
    main()


