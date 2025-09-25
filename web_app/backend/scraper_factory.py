"""
Dynamic scraper factory for email generation.
Creates appropriate scrapers based on email configuration.
"""
from typing import Dict, Any, Optional, Union
import asyncio
import logging

from aim.news.bailiwick_express_scraper import BEScraper
from aim.news.jep_scraper import JEPScraper
from aim.weather.gov_je import GovJeWeather
from aim.weather.gov_ge import GovGeWeather
from aim.family_notices import FamilyNotices

# Handle both relative and absolute imports
try:
    from .email_config import EmailTypeConfig, WeatherType
except ImportError:
    from email_config import EmailTypeConfig, WeatherType

logger = logging.getLogger(__name__)

class ScraperFactory:
    """Factory for creating and managing scrapers based on email configuration"""
    
    # Scraper class mappings
    NEWS_SCRAPERS = {
        "BEScraper": BEScraper,
        "JEPScraper": JEPScraper
    }
    
    WEATHER_SCRAPERS = {
        "GovJeWeather": GovJeWeather,
        "GovGeWeather": GovGeWeather
    }
    
    @classmethod
    async def create_scrapers_for_config(cls, config: EmailTypeConfig) -> Dict[str, Any]:
        """Create all required scrapers for an email configuration"""
        scrapers = {}
        
        # Create news scraper
        news_scraper_class = cls.NEWS_SCRAPERS.get(config.scraper_config.news_scraper)
        if news_scraper_class:
            scrapers["news"] = news_scraper_class()
        else:
            raise ValueError(f"Unknown news scraper: {config.scraper_config.news_scraper}")
        
        # Create weather scraper if needed
        if config.scraper_config.weather_scraper:
            weather_scraper_class = cls.WEATHER_SCRAPERS.get(config.scraper_config.weather_scraper)
            if weather_scraper_class:
                scrapers["weather"] = weather_scraper_class()
            else:
                raise ValueError(f"Unknown weather scraper: {config.scraper_config.weather_scraper}")
        
        # Create deaths scraper if needed (BE only currently)
        if config.scraper_config.deaths_scraper == "FamilyNoticesScraper":
            scrapers["deaths"] = FamilyNotices()
        
        return scrapers
    
    @classmethod
    async def close_scrapers(cls, scrapers: Dict[str, Any]):
        """Close all scrapers that have close methods"""
        close_tasks = []
        for scraper in scrapers.values():
            if hasattr(scraper, 'close'):
                close_tasks.append(scraper.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks)

class EmailDataBuilder:
    """Builds email data using configuration-driven approach"""
    
    @classmethod
    async def build_email_data(cls, config: EmailTypeConfig, request) -> Dict[str, Any]:
        """Build email data based on configuration and request"""
        scrapers = await ScraperFactory.create_scrapers_for_config(config)
        
        try:
            # Build tasks based on configuration
            tasks = {}
            news_scraper = scrapers["news"]
            
            # Add story scraping tasks
            for section, region in config.scraper_config.news_regions.items():
                count_attr = f"num_{section}"
                count = getattr(request, count_attr, 1)
                tasks[f"{section}_stories"] = news_scraper.get_n_stories_for_region(region, count)
            
            # Add weather task if configured
            if "weather" in scrapers:
                tasks["weather"] = scrapers["weather"].get_to_email()
            
            # Add deaths task if configured and dates provided
            if "deaths" in scrapers and request.deaths_start and request.deaths_end:
                from datetime import datetime
                start_date = datetime.fromisoformat(request.deaths_start) if request.deaths_start else None
                end_date = datetime.fromisoformat(request.deaths_end) if request.deaths_end else None
                tasks["family_notices"] = scrapers["deaths"].get_notices(start_date, end_date)
            
            # Add extra fields from configuration
            for field_name, value in config.scraper_config.extra_fields.items():
                if field_name == "connect_cover_region":
                    # Handle region-specific connect cover methods
                    if value == "jsy":
                        tasks["connect_cover_image"] = news_scraper.get_jsy_connect_cover()
                    else:  # gsy or other
                        tasks["connect_cover_image"] = news_scraper.get_gsy_connect_cover(value)
                elif field_name == "jep_cover_source":
                    # For JEP cover handling
                    from aim.news.jep_scraper import JEPScraper
                    cover_source = getattr(JEPScraper.JEPCoverSource, value, JEPScraper.JEPCoverSource.Jep)
                    tasks["jep_cover"] = news_scraper.get_cover(cover_source)
                    tasks["publication"] = news_scraper.get_cover(cover_source)
            
            # Execute all tasks
            values = await asyncio.gather(*tasks.values())
            results = dict(zip(tasks.keys(), values))
            
            return results
            
        finally:
            await ScraperFactory.close_scrapers(scrapers)
