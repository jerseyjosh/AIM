from typing import List
import datetime

import requests

from aim.transistor.models import User, AudioUpload, Show, Episode

class TransistorClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.transistor.fm/v1/"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def get_authenticated_user(self) -> User:
        response = requests.get(self.base_url, headers=self.headers)
        if response.status_code != 200:
            response.raise_for_status()
        return User(response.json())
    
    def authorize_upload(self, file_path: str) -> AudioUpload:
        url = self.base_url + "episodes/authorize_upload"
        response = requests.get(url, headers=self.headers, params={'filename': file_path})
        if response.status_code != 200:
            response.raise_for_status()
        return AudioUpload(response.json())
    
    def upload_audio(self, file_path: str, upload_url: str) -> dict:
        with open(file_path, 'rb') as f:
            headers = {'Content-Type': 'audio/mpeg'}
            response = requests.put(upload_url, data=f, headers=headers)
        if response.status_code != 200:
            response.raise_for_status()
        return response.json()
    
    def publish_episode(self, id: int, status: str, publish_at: str):
        assert status in ['draft', 'published', 'scheduled'], f"Invalid status: {status}, must be 'draft', 'published', or 'scheduled'"
        publish_at = datetime.datetime.strptime(publish_at, "%Y-%m-%dT%H:%M:%S")
        url = self.base_url + f"episodes/{id}/publish"
        data = {
            "episode[id]": id,
            "episode[status]": status,
            "episode[published_at]": publish_at
        }
        response = requests.patch(url, headers=self.headers, data=data)
        if response.status_code != 200:
            response.raise_for_status()
        return Episode(response.json())
    
    def create_episode(
            self,
            show_id: int,
            title: str,
            audio_url: str,
            author: str = None,
            description: str = None,
            transcript_text: str = None,
            **kwargs
    ):
        url = self.base_url + "episodes"
        data = {
            "show_id": show_id,
            "title": title,
            "audio_url": audio_url,
            "author": author,
            "description": description,
            "transcript_text": transcript_text,
        }
        data.update(kwargs)
        data = {k:v for k,v in data.items() if v is not None}
        response = requests.post(url, headers=self.headers, data=data)
        if response.status_code != 200:
            response.raise_for_status()
        return Episode(response.json())
    
    def get_shows(self) -> List[Show]:
        url = self.base_url + "shows"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            response.raise_for_status()
        return [Show(show) for show in response.json()['data']]
