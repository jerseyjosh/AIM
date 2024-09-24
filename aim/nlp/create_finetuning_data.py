import pandas as pd
import json

SYSTEM_PROMPT = "You are a professional journalist that creates news articles based on a set of bullet pointed notes. Do not include information you are not given. Return unicode formatted articles in the format <headline>...</headline><text>...</text>."
JSONL_PATH = 'finetuning_data.jsonl'

def load_finetune_data(path: str):
    return pd.read_csv(path)

def format_prompt(system_prompt: str, user_prompt: str, output: str) -> str:
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": output}
        ]
    }

def save_to_jsonl(message: dict, path: str):
    with open(path, 'a') as f:
        f.write(json.dumps(message) + '\n')

def main():

    # load data
    stories = load_finetune_data('finetuning_data.csv')
    stories = stories[stories['gpt_notes'].notnull()]

    # format data
    for i in range(len(stories)):
        story = stories.iloc[i]
        user_prompt = f'write a {story["n_words_round_100"]} word news article on the following notes: {story["gpt_notes"]}'
        output = story['full_article']
        message = format_prompt(SYSTEM_PROMPT, user_prompt, output)
        save_to_jsonl(message, JSONL_PATH)

if __name__ == "__main__":
    main()




