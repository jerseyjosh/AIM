""" Dataclasses for AIM objects """

from dataclasses import dataclass

@dataclass
class Advert:
    """
    Dataclass to hold advertisement information.
    """
    url: str
    image_url: str

    def __str__(self):
        return f"Advert(url={self.url}, image_url={self.image_url})"
    
    def __repr__(self):
        return str(self)

@dataclass
class NewsStory:
    """
    Dataclass to hold news story information.
    """
    headline: str
    text: str
    date: str
    author: str
    url: str
    image_url: str
    order: int = 0

    def __str__(self):
        # Limit the preview of the text to 100 characters
        text_preview = (self.text[:100] + '...') if len(self.text) > 100 else self.text
        return (f"NewsStory(\n"
                f"  Headline: {self.headline}\n"
                f"  Date: {self.date}\n"
                f"  Author: {self.author}\n"
                f"  Text: {text_preview}\n"
                f"  url: {self.url}\n"
                f"  image_url: {self.image_url}\n"
                f")")
    
    def __repr__(self):
        return str(self)