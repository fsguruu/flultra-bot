import aiohttp
import logging
import os

logger = logging.getLogger(__name__)
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

APIFY_RUN_URL = "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items"


async def fetch_instagram_via_apify(post_url: str) -> list[dict] | None:
    if not APIFY_API_TOKEN:
        logger.error("Ключ APIFY_API_TOKEN не знайдено в .env!")
        return None

    params = {"token": APIFY_API_TOKEN}
    payload = {
        "directUrls": [post_url],
        "resultsType": "posts",
        "resultsLimit": 1
    }

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(APIFY_RUN_URL, params=params, json=payload) as response:
                if response.status not in (200, 201):
                    text = await response.text()
                    logger.error(f"❌ Apify HTTP {response.status}: {text}")
                    return None

                data = await response.json()

                if not data:
                    return None

                item = data[0]
                media_collection = []

                if item.get("childPosts"):
                    for child in item["childPosts"]:
                        if child.get("videoUrl"):
                            media_collection.append({"type": "video", "url": child["videoUrl"]})
                        elif child.get("displayUrl"):
                            media_collection.append({"type": "photo", "url": child["displayUrl"]})
                elif item.get("videoUrl"):
                    media_collection.append({"type": "video", "url": item["videoUrl"]})
                elif item.get("displayUrl"):
                    media_collection.append({"type": "photo", "url": item["displayUrl"]})

                return media_collection if media_collection else None

    except Exception as e:
        logger.error(f"Помилка підключення до Apify: {e}")
        return None