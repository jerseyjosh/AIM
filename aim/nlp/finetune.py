import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

JSONL_PATH = 'finetuning_data.jsonl'
MODEL = "gpt-4o-mini-2024-07-18"

def get_openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv('OPENAI_KEY'))

def create_openai_file(client: OpenAI, path: str):
    with open(path, 'rb') as f:
        response = client.files.create(file=f, purpose='fine-tune')
        return response.id

def create_finetune_job(client: OpenAI, training_file: str):
    return client.fine_tuning.jobs.create(training_file=training_file, model=MODEL)

def check_finetune_jobs(client: OpenAI):
    jobs = client.fine_tuning.jobs.list()
    for job in jobs:
        print(job)

def list_files(client: OpenAI):
    print(client.files.list())

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Creating client.")
    client = get_openai_client()
    logging.info("Creating finetuning file.")
    file_id = create_openai_file(client, JSONL_PATH)
    logging.info(f"Created File ID: {file_id}")
    logging.info(f"Creating finetuning job for {file_id}")
    create_finetune_job(client, file_id)

if __name__ == "__main__":
    main()
    #check_finetune_jobs(get_openai_client())
    #list_files(get_openai_client())
    #create_openai_file(get_openai_client(), JSONL_PATH)
