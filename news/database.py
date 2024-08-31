import sqlite3
import logging

from typing import List, Literal
from news.models import NewsStory

logger = logging.getLogger(__name__)

def create_news_database(db_name: str):
    """
    Create a SQLite database with a table for news stories.
    """
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT,
                text TEXT,
                date TEXT,
                author TEXT,
                url TEXT
            )
        ''')
        conn.commit()
        logger.info(f"Database '{db_name}' created with table 'news_stories'.")
    except sqlite3.Error as e:
        logger.error(f"Failed to create database '{db_name}': {e}")
    finally:
        conn.close()

def insert_news_stories(db_name: str, stories: List[NewsStory]):
    """
    Insert a list of NewsStory objects into the database.
    """
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        # Prepare data to insert
        data = [(story.headline, story.date, story.author, story.text, story.url) for story in stories if isinstance(story, NewsStory)]
        # Insert data
        cursor.executemany('''
            INSERT INTO news_stories (headline, date, author, text, url)
            VALUES (?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
        logger.info(f"Inserted {len(data)} news stories into '{db_name}'.")
    except sqlite3.Error as e:
        logger.error(f"Failed to insert stories into database '{db_name}': {e}")
    finally:
        conn.close()


