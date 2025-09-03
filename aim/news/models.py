""" Dataclasses for AIM objects """
import re
from dataclasses import dataclass, field

@dataclass
class TopImage:
    title: str = field(default="")
    url: str = field(default="")
    author: str = field(default="")
    link: str = field(default="")

@dataclass
class FamilyNotice:

    name: str
    url: str
    funeral_director: str
    additional_text: str = ''

    def __post_init__(self):
        self.name = self.format_name(self.name)
        self.url = self.url.strip()

    def __str__(self):
        return self.name
    
    @staticmethod
    def format_name(name: str) -> str:
        """
        Formats a name from 'Last, First (Extra1) (Extra2)' to 'First Last (Extra1) (Extra2)'.
        Handles multiple parenthetical parts.
        """
        # Extract all bracketed parts
        bracketed_parts = re.findall(r"\(.*?\)", name)
        
        # Remove bracketed parts from the main name
        name_without_brackets = re.sub(r"\(.*?\)", "", name).strip()
        
        # Handle "Last, First" format
        if "," in name_without_brackets:
            last, first = [part.strip() for part in name_without_brackets.split(",", 1)]
            formatted_name = f"{first} {last}"
        else:
            formatted_name = name_without_brackets  # If no comma, assume already correct

        # Append all extracted bracketed parts at the end
        if bracketed_parts:
            formatted_name = f"{formatted_name} {' '.join(bracketed_parts)}"

        # Capitalize first letter of each word, except for 'née'
        return formatted_name.title().replace('Née', 'née')

@dataclass
class Advert:
    """
    Dataclass to hold advertisement information.
    """
    url: str
    image_url: str
    order: int = field(default=0)

@dataclass
class AdvertSection:
    adverts: list[Advert]

@dataclass(frozen=True)
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
    order: int = field(default=0)

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