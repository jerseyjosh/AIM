import asyncio

from openai import AsyncOpenAI
import tiktoken

from aim.news.models import NewsStory

SUMMARY_PROMPT = "Summarize the news story into a core set of facts."
SUMMARY_MODEL = "gpt-4o-mini"
TOKEN_LIMIT = 4096

async def get_news_summary(client: AsyncOpenAI, story: NewsStory) -> str:
    """
    Make request to OpenAI API to summarize news story into core set of facts.
    """
    full_article = story.headline + '\n' + story.text
    enc = tiktoken.encoding_for_model(SUMMARY_MODEL)
    n_tokens = len(enc.encode(full_article))

    response = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": story.headline+'\n'+story.text},
        ],
        model="gpt-4o-mini"
    )
    return response.choices[0].message.content

