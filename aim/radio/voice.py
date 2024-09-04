from elevenlabs.client import ElevenLabs
from elevenlabs import save

class VoiceGenerator:

    def __init__(self, api_key: str):
        self.client = ElevenLabs(api_key=api_key)

    def get_custom_voices(self):
        voices = self.client.voices.get_all().voices
        return [v for v in voices if v.name.lower().startswith('aim')]
    
    def generate(self, text: str, voice: str, model: str = 'eleven_turbo_v2_5'):
        return self.client.generate(text=text, voice=voice, model=model)
    

# if __name__=="__main__":

#     import asyncio
#     import os
#     from dotenv import load_dotenv, find_dotenv
#     load_dotenv(find_dotenv())

#     elevenlabs = VoiceGenerator(os.getenv("ELEVENLABS_API_KEY"))
#     audio = elevenlabs.generate("Hello, world!", "aim_christie")
#     breakpoint()