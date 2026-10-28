import os
import aiohttp
import logging

logger = logging.getLogger(__name__)

COBALT_LOCAL_URL = os.getenv("COBALT_URL", "http://cobalt-api:9000/")


async def fetch_media_from_cobalt(video_url: str) -> dict | None:
    """
    Получение ссылки на медиа через Cobalt.
    Cobalt является 1 уровнем в пайплайне загрузки медиа.
    Хендлит практически всё: Инсту, Тикток.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    payload_video = {
        "url": video_url,
        "videoQuality": "1080",
        # "videoCodec": "h264"
    }

    payload_audio = {
        "url": video_url,
        "downloadMode": "audio"
    }

    result = {
        "video_url": None,
        "audio_url": None,
        "caption": None,
        "picker": None
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:

            # ====================
            # 1. СКАЧИВАНИЕ ВИДЕО
            # ====================
            async with session.post(COBALT_LOCAL_URL, json=payload_video, headers=headers) as resp_vid:
                if resp_vid.status == 200:
                    data_vid = await resp_vid.json()
                    status = data_vid.get("status")

                    if status in ["redirect", "tunnel"]:
                        filename = data_vid.get("filename", "").lower()

                        if "instagram.com/reel" in video_url and filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
                            logger.warning("❌ Instagram отдал Cobalt превью. Переход на уровень ниже.")
                        else:
                            raw_url = data_vid.get("url", "")
                            result["video_url"] = raw_url.replace("localhost:9000", "cobalt-api:9000").replace(
                                "127.0.0.1:9000", "cobalt-api:9000")

                    elif status == "picker":
                        result["picker"] = data_vid.get("picker")
                else:
                    error_text = await resp_vid.text()
                    logger.error(f"❌ Cobalt [ВИДЕО] Ошибка HTTP {resp_vid.status}: {error_text}")


            if result["video_url"] or result["picker"]:
                async with session.post(COBALT_LOCAL_URL, json=payload_audio, headers=headers) as resp_aud:
                    if resp_aud.status == 200:
                        data_aud = await resp_aud.json()

                        if data_aud.get("status") in ["redirect", "tunnel"]:
                            raw_audio_url = data_aud.get("url", "")
                            result["audio_url"] = raw_audio_url.replace("localhost:9000", "cobalt-api:9000").replace(
                                "127.0.0.1:9000", "cobalt-api:9000")
                    else:
                        error_text = await resp_aud.text()
                        logger.error(f"❌ Cobalt [АУДІО] Ошибка HTTP {resp_aud.status}: {error_text}")

            if result["video_url"] or result["picker"]:
                return result

            return None

    except Exception as e:
        logger.error(f"❌ Ошибка Cobalt (недоступен контейнер?): {e}")
        return None