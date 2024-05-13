import logging
import openai

logger = logging.getLogger(__name__)

class Translator:

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

    def translate(self, text: str, to_language: str):
        assert to_language.lower() in self.LANGUAGES, f"Invalid language: {to_language}, choose from {self.LANGUAGES}"
        # make prompt
        prompt = f"""
        You are a translator designed to translate journalistic text whilst retaining meaning and adhering to journalistic standards.
        Return nothing but the output to the question.
        Translate the following text to {to_language}: {text}
        """
        # get response
        response = self.client.Completion.create(
            engine="gpt-4-turbo",
            prompt=prompt,
        )
        return response.choices[0].text.strip()

    