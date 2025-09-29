""" Dataclasses for AIM objects """
import re
from dataclasses import dataclass, field
from enum import Enum

class ForewordAuthor(Enum):
    Megan = (
        "Megan Davies", 
        "megan@allisland.media", 
        "https://i1.cmail19.com/ei/d/C9/5CF/E56/030608/csfinal/36909550-4228ec468d44ef4a.jpg",
        "Reporter, JEP and Bailiwick Express"
        )
    Christie = (
        "Christie Bailey", 
        "christie@allisland.media",
        "https://www.bailiwickexpress.com/wp-content/uploads/2025/09/5496290-683x1024.jpg",
        "News Editor, Bailiwick Express"
        )
    Fiona = (
        "Fiona Potigny", 
        "fiona@allisland.media", 
        "https://www.bailiwickexpress.com/wp-content/uploads/2025/09/5111912-865x1024.jpg",
        "Editor, Bailiwick Express"
        )

    @property
    def name(self):
        return self.value[0]
    
    @property
    def email(self):
        return self.value[1]

    @property
    def image_url(self):
        return self.value[2]
    
    @property
    def job_title(self):
        return self.value[3]

@dataclass
class Foreword:
    author: ForewordAuthor
    text: str
    title: str = "The best of our journalism"
    cryptic_clue: str = "One glass and he fails to stand up (7)"
    paras: list[str] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.paras = self.text.split("\n")

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