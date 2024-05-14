import logging
import openai

logger = logging.getLogger(__name__)

class Translator:

    SYSTEM_PROMPT = """"
    You are a translator designed to translate journalistic text whilst retaining meaning and adhering to journalistic standards.
    Return nothing but the requested text.
    Keep the phrase "Bailiwick Radio News" from English.
    """

    USER_PROMPT = """Translate the following to {}:\n{}"""

    LANGUAGES = [
        "english",
        "french",
        "portuguese",
        "polish",
        "romanian"
    ]

    def __init__(self, openai_key: str):
        self.openai_key = openai_key
        self.client = openai.Client(api_key=self.openai_key)

    def translate(self, text: str, to_language: str, model: str = "gpt-4o"):
        assert to_language.lower() in self.LANGUAGES, f"Invalid language: {to_language}, choose from {self.LANGUAGES}"
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": self.USER_PROMPT.format(to_language, text)}
            ]
        )
        logging.debug(f"Received response: {response}...'")
        return response.choices[0].message.content.strip()
    

if __name__=="__main__":

    # get key
    from dotenv import load_dotenv
    import os
    load_dotenv()
    openaia_key = os.getenv("OPENAI_API_KEY")

    # test translator
    translator = Translator(openai_key=openaia_key)
    text = "I am the Bailiwick news bot. I will destroy the british broadcasting corporation."
    response = translator.translate(text, "french")
    print(response)
    