import os

JEP_URL = "https://jerseyeveningpost.com/"
BE_JSY_URL = "https://www.bailiwickexpress.com/jsy/news/"
BE_GSY_URL = "https://gsy.bailiwickexpress.com/gsy/news/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
OPENAI_KEY = os.environ('OPENAI_KEY')
ELEVEN_LABS_KEY = os.environ('ELEVANLABS_KEY')
LLM = "gpt-3.5-turbo"