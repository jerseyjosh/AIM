from elevenlabs.client import ElevenLabs
from elevenlabs import save, VoiceSettings

class VoiceGenerator:

    MODEL = "eleven_multilingual_v2"
    SETTINGS = VoiceSettings(stability=0.75, similarity_boost=0.75, use_speaker_boost=False)

    def __init__(self, api_key: str):
        self.client = ElevenLabs(api_key=api_key)
        self.voice_to_id = {v.name: v.voice_id for v in self.get_custom_voices()}

    def get_custom_voices(self):
        voices = self.client.voices.get_all().voices
        return [v for v in voices if v.name.lower().startswith('aim')]
    
    def generate(self, text: str, voice: str):
        return self.client.text_to_speech.convert(voice_id=self.voice_to_id[voice], text=text, model_id=self.MODEL, voice_settings=self.SETTINGS)
    

if __name__=="__main__":

    import asyncio
    import os
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())

    elabs = VoiceGenerator(os.getenv("ELEVENLABS_API_KEY"))
    breakpoint()
