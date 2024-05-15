import logging
import json

import openai

logger = logging.getLogger(__name__)    

class LLM:

    SYSTEM_PROMPT = """
    You are a text processing AI tasked with translating input texts while applying specific modifications. For each input in the format {'text': text, 'language': language}, do the following:
    1. Translate the text into the specified language.
    2. Convert all numbers and currency symbols to their contextually and grammatically correct word equivalents.
    3. Do not translate proper nouns, names, or the phrase "Bailiwick Radio News".
    4. Format the output to be clearly readable and unambiguous.
    Return the transformed text only.
    """

    LANGUAGES = [
        "english",
        "french",
        "portuguese",
        "polish",
        "romanian"
    ]

    def __init__(self, openai_api_key: str):
        self.client = openai.Client(api_key=openai_api_key)

    @staticmethod
    def _get_user_prompt(text: str, language: str):
        return json.dumps({"text": text, "language": language})
    
    def process(self, text: str, to_language: str, model: str = "gpt-4o"):
        assert to_language.lower() in self.LANGUAGES, f"Invalid language: {to_language}, choose from {self.LANGUAGES}"
        user_prompt = self._get_user_prompt(text, to_language)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        logging.debug(f"Sending request to OpenAI API with model: {model} and messages: {messages}...'")
        response = self.client.chat.completions.create(model=model, messages=messages)
        logging.debug(f"Received response: {response}'")
        return response.choices[0].message.content.strip()
    

if __name__=="__main__":

    from dotenv import load_dotenv
    import os
    import tiktoken

    openai_api_key = os.getenv("OPENAI_API_KEY")

    enc = tiktoken.encoding_for_model("gpt-4o")

    llm = LLM(openai_api_key)
    text = "The man had spent $16000 worth of £1000 notes in the Bailiwick of Guernsey."
    translated_text = llm.process(text, "english")  
    print(translated_text)
    breakpoint()
    