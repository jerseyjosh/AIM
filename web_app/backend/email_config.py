"""
Email Configuration System
Defines email types and their properties in a modular way.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

class AdvertType(Enum):
    VERTICAL_HORIZONTAL = "vertical_horizontal"  # BE/GE style with both types
    SINGLE = "single"  # JEP style with single list

class WeatherType(Enum):
    JERSEY = "jersey"
    GUERNSEY = "guernsey" 
    NONE = "none"

@dataclass
class ScraperConfig:
    """Configuration for scrapers used by this email type"""
    news_scraper: str  # Class name like "BEScraper", "JEPScraper"
    news_regions: Dict[str, str]  # {"news": "jsy_news", "business": "jsy_business"}
    weather_scraper: Optional[str] = None
    deaths_scraper: Optional[str] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)  # For jep_cover, etc.

@dataclass
class EmailTypeConfig:
    """Complete configuration for an email type"""
    id: str
    name: str
    scraper_config: ScraperConfig
    advert_type: AdvertType
    weather_type: WeatherType
    story_sections: List[str]  # ["news", "business", "sports", "community", "podcast"]
    ui_features: Dict[str, bool] = field(default_factory=dict)  # {"show_weather_edit": True}
    template_fields: Dict[str, Any] = field(default_factory=dict)  # Extra template data

# Email type registry
EMAIL_CONFIGS = {
    "be": EmailTypeConfig(
        id="be",
        name="Bailiwick Express (Jersey)",
        scraper_config=ScraperConfig(
            news_scraper="BEScraper",
            news_regions={
                "news": "jsy_news",
                "business": "jsy_business", 
                "sports": "jsy_sport",
                "community": "jsy_community",
                "podcast": "jsy_podcasts"
            },
            weather_scraper="GovJeWeather",
            deaths_scraper="FamilyNoticesScraper",
            extra_fields={"connect_cover_region": "jsy"}
        ),
        advert_type=AdvertType.VERTICAL_HORIZONTAL,
        weather_type=WeatherType.JERSEY,
        story_sections=["news", "business", "sports", "community", "podcast"],
        ui_features={"show_weather_edit": True, "show_family_notices": True}
    ),
    
    "ge": EmailTypeConfig(
        id="ge", 
        name="Bailiwick Express (Guernsey)",
        scraper_config=ScraperConfig(
            news_scraper="BEScraper",
            news_regions={
                "news": "gsy_news",
                "business": "gsy_business",
                "sports": "gsy_sport", 
                "community": "gsy_community",
                "podcast": "jsy_podcasts"  # Uses Jersey podcasts
            },
            weather_scraper="GovGeWeather",
            extra_fields={"connect_cover_region": "gsy"}
        ),
        advert_type=AdvertType.VERTICAL_HORIZONTAL,
        weather_type=WeatherType.GUERNSEY,
        story_sections=["news", "business", "sports", "community", "podcast"],
        ui_features={"show_weather_edit": True}
    ),
    
    "jep": EmailTypeConfig(
        id="jep",
        name="Jersey Evening Post",
        scraper_config=ScraperConfig(
            news_scraper="JEPScraper", 
            news_regions={
                "news": "jsy_news",
                "business": "jsy_business",
                "sports": "jsy_sport"
            },
            extra_fields={"jep_cover_source": "JEP"}
        ),
        advert_type=AdvertType.SINGLE,
        weather_type=WeatherType.NONE,
        story_sections=["news"],  # JEP combines all into single news list
        ui_features={"combine_all_stories": True, "show_publication_cover": True},
        template_fields={"date_format": "%A %-d %B %Y"}
    )
}

def get_email_config(email_type: str) -> EmailTypeConfig:
    """Get configuration for an email type"""
    if email_type not in EMAIL_CONFIGS:
        raise ValueError(f"Unknown email type: {email_type}. Valid types: {list(EMAIL_CONFIGS.keys())}")
    return EMAIL_CONFIGS[email_type]

def get_valid_email_types() -> List[str]:
    """Get list of valid email type IDs"""
    return list(EMAIL_CONFIGS.keys())

def get_email_type_names() -> Dict[str, str]:
    """Get mapping of email type IDs to human-readable names"""
    return {config.id: config.name for config in EMAIL_CONFIGS.values()}
