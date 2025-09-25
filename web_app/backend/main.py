import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from aim.news.bailiwick_express_scraper import BEScraper
from aim.news.jep_scraper import JEPScraper
from aim.weather.gov_je import GovJeWeather
from aim.weather.gov_ge import GovGeWeather
from aim.family_notices import FamilyNotices
from aim.news.models import NewsStory, FamilyNotice, TopImage, Advert
from aim.emailer.base import EmailBuilder

logger = logging.getLogger(__name__)

app = FastAPI(title="BE Email Generator", description="Internal tool for generating BE emails")

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For internal use only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic auth for simple security
security = HTTPBasic()

# Load credentials
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
    STREAMLIT_USER = os.getenv("STREAMLIT_USER", "admin")
    STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD", "password")
except Exception:
    STREAMLIT_USER = "admin"
    STREAMLIT_PASSWORD = "password"

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != STREAMLIT_USER or credentials.password != STREAMLIT_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials

# Mount static files
import os
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
static_path = os.path.join(frontend_path, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Pydantic models
class NewsStoryResponse(BaseModel):
    order: int
    headline: str
    text: str
    author: str
    date: str
    url: str
    image_url: str

class FamilyNoticeResponse(BaseModel):
    name: str
    funeral_director: str
    additional_text: str
    url: str

class TopImageResponse(BaseModel):
    title: str = ""
    url: str = ""
    author: str = ""
    link: str = ""

class AdvertResponse(BaseModel):
    order: int
    url: str
    image_url: str

class EmailDataRequest(BaseModel):
    email_type: str = Field(default="be", pattern="^(be|ge|jep)$")
    num_news: int = Field(default=7, ge=1, le=20)
    num_business: int = Field(default=1, ge=1, le=20)
    num_sports: int = Field(default=1, ge=1, le=20)
    num_community: int = Field(default=1, ge=1, le=20)
    num_podcast: int = Field(default=1, ge=1, le=20)
    deaths_start: str = ""  # ISO date string - optional for JEP/GE
    deaths_end: str = ""    # ISO date string - optional for JEP/GE

class WeatherResponse(BaseModel):
    todays_weather: str = ""
    tides: str = ""
    date: str = ""

class EmailDataResponse(BaseModel):
    email_type: str
    news_stories: List[NewsStoryResponse]
    business_stories: List[NewsStoryResponse] = []
    sports_stories: List[NewsStoryResponse] = []
    community_stories: List[NewsStoryResponse] = []
    podcast_stories: List[NewsStoryResponse] = []
    weather: WeatherResponse = WeatherResponse()
    family_notices: List[FamilyNoticeResponse] = []
    connect_cover_image: str = ""
    jep_cover: str = ""  # For JEP emails
    publication: str = ""  # For JEP emails
    date: str = ""  # For JEP emails

class ManualUrlsRequest(BaseModel):
    urls: List[str]

class GenerateEmailRequest(BaseModel):
    email_type: str = "be"
    news_stories: List[dict] = []
    business_stories: List[dict] = []
    sports_stories: List[dict] = []
    community_stories: List[dict] = []
    podcast_stories: List[dict] = []
    weather: dict = {}
    family_notices: List[dict] = []
    connect_cover_image: str = ""
    top_image: dict = {}
    vertical_adverts: List[dict] = []
    horizontal_adverts: List[dict] = []
    # JEP-specific fields
    jep_cover: str = ""
    publication: str = ""
    date: str = ""
    adverts: List[dict] = []  # JEP uses single advert list

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    html_path = os.path.join(frontend_path, "index.html")
    with open(html_path, "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/fetch-data")
async def fetch_email_data(
    request: EmailDataRequest,
    credentials: HTTPBasicCredentials = Depends(verify_credentials)
) -> EmailDataResponse:
    """Fetch all data for email generation"""
    try:
        # Convert helper functions
        def story_to_response(story: NewsStory) -> NewsStoryResponse:
            return NewsStoryResponse(
                order=story.order,
                headline=story.headline,
                text=story.text,
                author=story.author,
                date=story.date.isoformat() if hasattr(story.date, 'isoformat') else str(story.date),
                url=story.url,
                image_url=story.image_url
            )

        def notice_to_response(notice: FamilyNotice) -> FamilyNoticeResponse:
            return FamilyNoticeResponse(
                name=notice.name,
                funeral_director=notice.funeral_director,
                additional_text=notice.additional_text,
                url=notice.url
            )
        
        # Handle different email types
        if request.email_type == "be":
            # BE Email - Jersey focused
            deaths_start = datetime.fromisoformat(request.deaths_start) if request.deaths_start else None
            deaths_end = datetime.fromisoformat(request.deaths_end) if request.deaths_end else None
            
            news_scraper = BEScraper()
            weather_scraper = GovJeWeather()
            deaths_scraper = FamilyNotices() if deaths_start and deaths_end else None

            tasks = {
                "news_stories": news_scraper.get_n_stories_for_region("jsy", request.num_news),
                "business_stories": news_scraper.get_n_stories_for_region("jsy_business", request.num_business),
                "sports_stories": news_scraper.get_n_stories_for_region("jsy_sport", request.num_sports),
                "community_stories": news_scraper.get_n_stories_for_region("jsy_community", request.num_community),
                "podcast_stories": news_scraper.get_n_stories_for_region("jsy_podcasts", request.num_podcast),
                "connect_cover_image": news_scraper.get_jsy_connect_cover(),
                "weather": weather_scraper.get_to_email(),
            }
            
            if deaths_scraper:
                tasks["family_notices"] = deaths_scraper.get_notices(deaths_start, deaths_end)
            
            values = await asyncio.gather(*tasks.values())
            results = dict(zip(tasks.keys(), values))
            
            # Close scrapers
            close_tasks = [news_scraper.close()]
            if deaths_scraper:
                close_tasks.append(deaths_scraper.close())
            await asyncio.gather(*close_tasks)
            
            return EmailDataResponse(
                email_type="be",
                news_stories=[story_to_response(s) for s in results["news_stories"]],
                business_stories=[story_to_response(s) for s in results["business_stories"]],
                sports_stories=[story_to_response(s) for s in results["sports_stories"]],
                community_stories=[story_to_response(s) for s in results["community_stories"]],
                podcast_stories=[story_to_response(s) for s in results["podcast_stories"]],
                weather=WeatherResponse(**results["weather"]) if results["weather"] else WeatherResponse(),
                family_notices=[notice_to_response(n) for n in results.get("family_notices", [])],
                connect_cover_image=results["connect_cover_image"]
            )
            
        elif request.email_type == "ge":
            # GE Email - Guernsey focused
            news_scraper = BEScraper()
            weather_scraper = GovGeWeather()

            tasks = {
                "news_stories": news_scraper.get_n_stories_for_region("gsy", request.num_news),
                "business_stories": news_scraper.get_n_stories_for_region("gsy_business", request.num_business),
                "sports_stories": news_scraper.get_n_stories_for_region("gsy_sport", request.num_sports),
                "community_stories": news_scraper.get_n_stories_for_region("gsy_community", request.num_community),
                "podcast_stories": news_scraper.get_n_stories_for_region("jsy_podcasts", request.num_podcast),
                "connect_cover_image": news_scraper.get_connect_cover("gsy"),
                "weather": weather_scraper.get_to_email(),
            }
            
            values = await asyncio.gather(*tasks.values())
            results = dict(zip(tasks.keys(), values))
            
            await news_scraper.close()
            
            return EmailDataResponse(
                email_type="ge",
                news_stories=[story_to_response(s) for s in results["news_stories"]],
                business_stories=[story_to_response(s) for s in results["business_stories"]],
                sports_stories=[story_to_response(s) for s in results["sports_stories"]],
                community_stories=[story_to_response(s) for s in results["community_stories"]],
                podcast_stories=[story_to_response(s) for s in results["podcast_stories"]],
                weather=WeatherResponse(**results["weather"]) if results["weather"] else WeatherResponse(),
                connect_cover_image=results["connect_cover_image"]
            )
            
        elif request.email_type == "jep":
            # JEP Email - Different structure
            news_scraper = JEPScraper()
            
            tasks = {
                "news_stories": news_scraper.get_n_stories_for_region("jsy_news", request.num_news),
                "business_stories": news_scraper.get_n_stories_for_region("jsy_business", request.num_business),
                "sports_stories": news_scraper.get_n_stories_for_region("jsy_sport", request.num_sports),
                "jep_cover": news_scraper.get_cover(JEPScraper.JEPCoverSource.Jep),
                "publication": news_scraper.get_cover(JEPScraper.JEPCoverSource.Jep),  # Default to JEP
            }
            
            values = await asyncio.gather(*tasks.values())
            results = dict(zip(tasks.keys(), values))
            
            await news_scraper.close()
            
            # Combine all stories for JEP (they use single news_stories list)
            all_news = results["news_stories"] + results["business_stories"] + results["sports_stories"]
            
            return EmailDataResponse(
                email_type="jep",
                news_stories=[story_to_response(s) for s in all_news],
                jep_cover=results["jep_cover"],
                publication=results["publication"],
                date=datetime.now().strftime("%A %-d %B %Y")
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid email type: {request.email_type}")

    except Exception as e:
        logger.error(f"Error fetching email data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scrape-urls")
async def scrape_manual_urls(
    request: ManualUrlsRequest,
    credentials: HTTPBasicCredentials = Depends(verify_credentials)
) -> List[NewsStoryResponse]:
    """Manually scrape a list of URLs"""
    try:
        scraper = BEScraper()
        stories = await scraper.fetch_and_parse_stories(request.urls)
        await scraper.close()
        
        valid_stories = [s for s in stories if s and not isinstance(s, Exception)]
        
        def story_to_response(story: NewsStory) -> NewsStoryResponse:
            return NewsStoryResponse(
                order=story.order,
                headline=story.headline,
                text=story.text,
                author=story.author,
                date=story.date.isoformat() if hasattr(story.date, 'isoformat') else str(story.date),
                url=story.url,
                image_url=story.image_url
            )
        
        return [story_to_response(s) for s in valid_stories]

    except Exception as e:
        logger.error(f"Error scraping URLs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-html")
async def test_html():
    """Test endpoint that returns simple HTML"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test HTML</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #f0f0f0; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>Test Email Preview</h1>
        <p>This is a test to verify that the iframe can display HTML content.</p>
        <p>Current time: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </body>
    </html>
    """
    return {"html": html}

@app.post("/api/generate-email")
async def generate_email(
    request: GenerateEmailRequest,
    credentials: HTTPBasicCredentials = Depends(verify_credentials)
):
    """Generate the final email HTML"""
    try:
        # Validate that we have news stories
        if not request.news_stories or len(request.news_stories) == 0:
            raise HTTPException(status_code=400, detail="No news stories provided")
        
        logger.info(f"Generating {request.email_type} email with {len(request.news_stories)} news stories")
        from dataclasses import dataclass
        
        # Choose the correct email builder based on type
        if request.email_type == "be":
            email_builder = EmailBuilder.BE()
            
            @dataclass
            class BEEmailData:
                news_stories: list
                business_stories: list
                sports_stories: list
                community_stories: list
                podcast_stories: list
                weather: dict
                family_notices: list
                connect_cover_image: str
                top_image: dict
                vertical_adverts: list = None
                horizontal_adverts: list = None
            
            template_data = BEEmailData(
                news_stories=request.news_stories,
                business_stories=request.business_stories,
                sports_stories=request.sports_stories,
                community_stories=request.community_stories,
                podcast_stories=request.podcast_stories,
                weather=request.weather,
                family_notices=request.family_notices,
                connect_cover_image=request.connect_cover_image,
                top_image=request.top_image,
                vertical_adverts=request.vertical_adverts or [],
                horizontal_adverts=request.horizontal_adverts or []
            )
            
        elif request.email_type == "ge":
            email_builder = EmailBuilder.Gsy()
            
            @dataclass
            class GEEmailData:
                news_stories: list
                business_stories: list
                sports_stories: list
                community_stories: list
                podcast_stories: list
                weather: dict
                connect_cover_image: str
                top_image: dict
                vertical_adverts: list = None
                horizontal_adverts: list = None

            template_data = GEEmailData(
                news_stories=request.news_stories,
                business_stories=request.business_stories,
                sports_stories=request.sports_stories,
                community_stories=request.community_stories,
                podcast_stories=request.podcast_stories,
                weather=request.weather,
                connect_cover_image=request.connect_cover_image,
                top_image=request.top_image,
                vertical_adverts=request.vertical_adverts or [],
                horizontal_adverts=request.horizontal_adverts or []
            )
            
        elif request.email_type == "jep":
            email_builder = EmailBuilder.JEP()
            
            @dataclass
            class JEPEmailData:
                news_stories: list
                adverts: list
                jep_cover: str
                publication: str
                date: str

            template_data = JEPEmailData(
                news_stories=request.news_stories,
                adverts=request.adverts,
                jep_cover=request.jep_cover,
                publication=request.publication,
                date=request.date or datetime.now().strftime("%A %-d %B %Y")
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Invalid email type: {request.email_type}")
        
        # Generate the HTML
        html_content = email_builder.render(template_data)
        
        return {"html": html_content}
    
    except Exception as e:
        logger.error(f"Error generating email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
