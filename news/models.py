from dataclasses import dataclass

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

    def __str__(self):
        # Limit the preview of the text to 100 characters
        text_preview = (self.text[:100] + '...') if len(self.text) > 100 else self.text
        return (f"NewsStory(\n"
                f"  Headline: {self.headline}\n"
                f"  Date: {self.date}\n"
                f"  Author: {self.author}\n"
                f"  Text: {text_preview}\n"
                f"  URL: {self.url}\n"
                f")")
    
    def __repr__(self):
        return str(self)