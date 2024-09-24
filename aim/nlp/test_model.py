import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from openai import OpenAI

SYSTEM_PROMPT = "You are a professional journalist that creates news articles based on a set of bullet pointed notes. Do not include information you are not given. Return unicode formatted articles in the format <headline>...</headline><text>...</text>."
FINETUNE_MODEL = "ft:gpt-4o-mini-2024-07-18:personal::AB3GrlLu"
USER_PROMPT = """
- Ongoing concerns over Jersey's bed blocking issues
- Islanders facing hospital discharge delays due to carer shortages
- Jersey Care Federation warns of "no movement" on the issue in recent years
- 'Bed blocking' defined as medically fit patients staying in hospital due to lack of care options
- 32 patients last week unable to leave hospital despite being medically fit
- Main causes: lack of nursing home beds, specialist care, and community care packages
- Discharge planning starts upon hospital admission
- Recruitment pressures in nursing and care sectors affecting bed availability
- Global and local shortages impacting discharge timeliness
"""

def get_openai_client():
    return OpenAI(api_key=os.getenv('OPENAI_KEY'))

def format_user_prompt(n_words: int, notes: str):
    return USER_PROMPT.format(n_words, notes)

def get_article(client: OpenAI, model: str = FINETUNE_MODEL):
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        model="gpt-4o-mini"
    )
    return response.choices[0].message.content

def main():
    client = get_openai_client()
    print(get_article(client))

if __name__ == "__main__":
    main()

