import aiohttp
import os
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from urllib.parse import urljoin

class MeteoWeather:

    BASE_URL = "https://api.meteomatics.com/"
    ST_HELIER_COORDS = (49.1856637,-2.1102277)
    ST_HELIER_ABOVE_SEALEVEL = "2m"
    WEATHER_SYMBOL_MAP = {
        0: "A weather symbol could not be determined",
        1: "Clear sky",
        2: "Light clouds",
        3: "Partly cloudy",
        4: "Cloudy",
        5: "Rain",
        6: "Rain and snow / sleet",
        7: "Snow",
        8: "Rain shower",
        9: "Snow shower",
        10: "Sleet shower",
        11: "Light Fog",
        12: "Dense fog",
        13: "Freezing rain",
        14: "Thunderstorms",
        15: "Drizzle",
        16: "Sandstorm"
    }

    def __init__(self, user, password):
        self.session = aiohttp.ClientSession()
        self.base_url = "https://api.meteomatics.com/"
        self.user = user
        self.password = password

    async def get_weather_symbol(self, location: Optional[tuple[str]] = None, timerange: Optional[str] = None):
        """
        Get the weather for St Helier.
        """
        if not location:
            location = self.ST_HELIER_COORDS
        if not timerange:
            timerange = self.timerange_today()
        url = self.make_url(
            timerange=timerange,
            parameters=self.weather_symbol_param(),
            location=','.join(map(str,location)),
            output='json'
        )
        async with self.session.get(url, auth=aiohttp.BasicAuth(self.user, self.password)) as response:
            return await response.json()
        
    def parse_weather_response(self, response):
        """
        Parse the weather response and return a human readable string.
        """
        data = response['data'][0]
        
        
    def join_param_strings(self, *params):
        """
        Generate a parameter string for the given parameters.
        """
        return ",".join(params)
    
    def weather_symbol_param(self, period: str = "24h"):
        """
        Generate the parameter string for weather symbols.
        """
        if period not in ["24h", "1h"]:
            raise ValueError(f"Invalid period, must be one of '24h' or '1h', got {period}")
        return f"weather_symbol_{period}:idx"
        
    def temperature_param(self, altitude: str, unit: str):
        """
        Generate the parameter string for temperature at a given altitude.
        """
        return f"t_{altitude}m:{unit}"

    def make_url(self, timerange: str, parameters: str, location: str, output: str, optionals: Optional[str] = ''):
        """
        Generate the full URL for a weather query.
        """
        tail = "/".join([timerange, parameters, location, output + '?' + optionals])
        return urljoin(self.base_url, tail)
        
    def timerange_today(self):
        """
        Get the timerange for today.
        """
        return (
            datetime.today().date().strftime("%Y-%m-%dT%H:%M:%SZ") 
            + "--" + (datetime.today().date() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def timestamp(self):
        """
        Get timestamp in meteomatic format: 2024-12-31T23:59:59Z 
        """
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__=="__main__":

    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())

    async def main():
        weather = MeteoWeather(os.getenv("METEO_USER"), os.getenv("METEO_PASSWORD"))
        response = await weather.get_weather_symbol()
        breakpoint()

    import uvloop
    uvloop.run(main())