import aiohttp
import aiolimiter

class FamilyNoticesScraper:
    def __init__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None))
        self.limiter = aiolimiter.AsyncLimiter(100, 1)

    