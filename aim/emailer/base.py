from typing import Optional, Dict, List, Any
import os
import asyncio
import uvloop
import logging
import jinja2
from dataclasses import dataclass, field, asdict
from datetime import datetime

from aim.news import BEScraper, JEPScraper
from aim.news.models import NewsStory, Advert, TopImage
from aim.weather.gov_je import GovJeWeather
from aim.family_notices import FamilyNotices

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


class EmailBuilder:

    @classmethod
    def JEP(cls):
        return Email(template_name="jep_template.html")
    
    @classmethod
    def BE(cls):
        return Email(template_name="be_template.html")
    
    @classmethod
    def Gsy(cls):
        return Email(template_name="ge_template.html")
    
class Email:
    def __init__(self, template_name: str):
        self.template_name = template_name
        self.template_loader = jinja2.FileSystemLoader(TEMPLATES_DIR)
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["first_sentence"] = self.first_sentence
        self.template = self.template_env.get_template(self.template_name)

    def render(self, data) -> str:
        """Render the email template with the current data."""
        return self.template.render(asdict(data))

    @staticmethod
    def first_sentence(text: Optional[str]) -> str:
        """Extract the first sentence from a string, for passing to Jinja"""
        if not text:
            return ""
        first = text.split(".")[0]
        return first + "." if first and not first.endswith(".") else first