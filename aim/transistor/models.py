class User:
    """The current Transistor user account authenticated for the API."""
    def __init__(self, response_json: dict):
        data: dict = response_json['data']['attributes']
        self.created_at = data.get('created_at')
        self.image_url = data.get('image_url')
        self.name = data.get('name')
        self.time_zone = data.get('time_zone')
        self.updated_at = data.get('updated_at')
    def __str__(self):
        return f"User(name={self.name}, created_at={self.created_at}, updated_at={self.updated_at}, time_zone={self.time_zone}, image_url={self.image_url})"

class AudioUpload:
    """Authorized audio upload resource, including the upload_url to upload the audio file to, and the content_type to use when uploading."""
    def __init__(self, response_json: dict):
        data: dict = response_json['data']['attributes']
        self.audio_url = data.get("audio_url")
        self.content_type = data.get("content_type")
        self.expires_in = data.get("expires_in")
        self.upload_url = data.get("upload_url")
    def __str__(self):
        return f"AudioUpload(audio_url={self.audio_url}, content_type={self.content_type}, expires_in={self.expires_in}, upload_url={self.upload_url})"
    
class Show:
    """An individual Transistor show (podcast)."""
    def __init__(self, data: dict):
        self.id = data.get('id', None)
        attributes: dict = data.get('attributes', {})
        for k,v in attributes:
            setattr(self, k, v)
    def __str__(self):
        return f"Show(title={self.title}, id={self.id})"
    
class ShowList:
    """A list of Transistor shows (podcasts)."""
    def __init__(self, data: dict):
        self.shows = [Show(show) for show in data['data']]
    def __str__(self):
        return f"ShowList({self.shows})"
    
class Episode:
    """An individual Transistor podcast episode record."""
    def __init__(self, data):
        self.data = data
    def __str__(self):
        return f"Episode({self.data})"
