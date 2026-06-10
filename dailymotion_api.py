import asyncio
import logging
from typing import List
import aiohttp

logger = logging.getLogger(__name__)

FORBIDDEN_LANGUAGE_MARKERS = [
    "hindi", "indonesian", "tamil", "telugu", "malay", "urdu",
    "arabic", "thai", "vietnamese", "spanish", "french", "german",
    "portuguese", "chinese", "japanese", "korean", "russian",
]

class DailymotionClient:
    BASE_URL = "https://api.dailymotion.com/videos"
    TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)

    @staticmethod
    async def _search(session: aiohttp.ClientSession, query: str, limit: int = 5, dubbed_only: bool = False) -> List[dict]:
        params = {
            "search": query,
            "limit": limit if not dubbed_only else max(limit * 4, 50),
            "fields": "id,title,description,channel,embed_url",
            "sort": "relevance",
        }
        try:
            async with session.get(DailymotionClient.BASE_URL, params=params, timeout=DailymotionClient.TIMEOUT) as resp:
                if resp.status != 200:
                    logger.error(f"API returned {resp.status}")
                    return []
                data = await resp.json()
                items = data.get("list", [])
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"Network error: {e}")
            return []

        results = []
        for video in items:
            title = video.get("title", "")
            description = video.get("description", "")
            if dubbed_only:
                combined = f"{title} {description}".lower()
                if any(marker in combined for marker in FORBIDDEN_LANGUAGE_MARKERS):
                    continue
            
            results.append({
                "id": video["id"],
                "title": title,
                "description": description,
                "url": f"https://www.dailymotion.com/video/{video['id']}",
            })
            if len(results) == limit:
                break
        return results

    @classmethod
    async def search(cls, query: str, limit: int = 5) -> List[dict]:
        async with aiohttp.ClientSession() as session:
            return await cls._search(session, query, limit=limit, dubbed_only=False)

    @classmethod
    async def dubbed_search(cls, query: str, limit: int = 5) -> List[dict]:
        async with aiohttp.ClientSession() as session:
            return await cls._search(session, query, limit=limit, dubbed_only=True)
