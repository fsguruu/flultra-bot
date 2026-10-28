import os
import logging
import asyncio
from aiogram import types
from services.core.cobalt_engine import fetch_media_from_cobalt
from services.core.ytdlp_engine import sync_download_video, get_media_caption, extract_audio_ytdlp
from services.utils_service import format_caption, is_fake_file, download_temp_file
from services.telegram_sender import send_universal_media
from services.core.apify_engine import fetch_instagram_via_apify
from messages import msgs

logger = logging.getLogger(__name__)


async def get_raw_audio(url: str, cobalt_data: dict = None) -> tuple:
    audio_path = None
    if cobalt_data and cobalt_data.get("audio_url"):
        audio_path = await download_temp_file(cobalt_data["audio_url"])
        if audio_path and audio_path.endswith((".jpg", ".png")):
            os.remove(audio_path)
            audio_path = None

    title, performer = "Instagram Audio", "Unknown Artist"
    if not audio_path or is_fake_file(audio_path):
        audio_path, yt_title, yt_performer = await extract_audio_ytdlp(url)
        if yt_title: title = yt_title
        if yt_performer: performer = yt_performer

    return audio_path if not is_fake_file(audio_path) else None, title, performer


async def process_instagram(url: str, message: types.Message, wait_msg: types.Message):
    video_path = None
    audio_path = None
    cover_donor_path = None

    try:
        # ===============================================================
        # Уровень 1: Cobalt (Селф-хост, хендлит 90% всех запросов)
        # ===============================================================
        cobalt_data = await fetch_media_from_cobalt(url)
        await wait_msg.edit_text(msgs.DOWNLOADING.format(tag="IG"))
        if cobalt_data:
            original_caption = await get_media_caption(url)
            caption = format_caption(url, original_caption)

            audio_path, audio_title, audio_performer = await get_raw_audio(url, cobalt_data)

            media_data = {
                "caption": caption,
                "audio_path": audio_path,
                "audio_title": audio_title,
                "audio_performer": audio_performer
            }

            # === Кейс 1: Карусель (Фотки) ===
            if cobalt_data.get("picker"):
                media_data["type"] = "carousel"
                picker = cobalt_data["picker"]
                media_data["carousel_items"] = [{"type": item.get("type", "photo"), "url": item["url"]} for item in
                                                picker]

                if picker:
                    cover_donor_path = await download_temp_file(picker[0]["url"])
                    media_data["avatar_path"] = cover_donor_path

            # === Кейс 2: Видео либо одно фото ===
            elif cobalt_data.get("video_url"):
                media_data["type"] = "video"
                video_path = await download_temp_file(cobalt_data["video_url"])
                media_data["video_path"] = video_path if not is_fake_file(video_path) else None

            await send_universal_media(message, wait_msg, media_data)
            return

        # ===============================================================
        # Уровень 2: Apify (Внешний API, 1к запросов / мес)
        # ===============================================================
        await wait_msg.edit_text(msgs.DOWNLOADING_SECOND.format(tag="IG"))
        media_list = await fetch_instagram_via_apify(url)

        logger.info("[TIMING] apify done")

        if media_list:
            original_caption = await get_media_caption(url)
            logger.info("[TIMING] caption done")
            caption = format_caption(url, original_caption)

            audio_path, audio_title, audio_performer = await get_raw_audio(url)

            logger.info("[TIMING] audio done")

            media_data = {
                "caption": caption,
                "audio_path": audio_path,
                "audio_title": audio_title,
                "audio_performer": audio_performer
            }

            if len(media_list) == 1:
                item = media_list[0]
                media_data["type"] = "video"
                video_path = await download_temp_file(item["url"])
                media_data["video_path"] = video_path if not is_fake_file(video_path) else None
            else:
                media_data["type"] = "carousel"
                media_data["carousel_items"] = [{"type": item["type"], "url": item["url"]} for item in media_list]
                cover_donor_path = await download_temp_file(media_list[0]["url"])
                media_data["avatar_path"] = cover_donor_path

            await send_universal_media(message, wait_msg, media_data)
            return

        # ===============================================================
        # Уровень 3: YT-DLP (Локальный, хендлит 99,9% данных)
        # ===============================================================
        await wait_msg.edit_text(msgs.DOWNLOADING_THIRD.format(tag="IG"))
        video_path = await asyncio.to_thread(sync_download_video, url)

        if video_path and not is_fake_file(video_path):
            original_caption = await get_media_caption(url)
            audio_path, audio_title, audio_performer = await extract_audio_ytdlp(url)

            media_data = {
                "type": "video",
                "video_path": video_path,
                "caption": format_caption(url, original_caption),
                "audio_path": audio_path if not is_fake_file(audio_path) else None,
                "audio_title": audio_title,
                "audio_performer": audio_performer
            }

            await send_universal_media(message, wait_msg, media_data)
            return

        await wait_msg.edit_text(msgs.IG_DOWNLOAD_FAILED)

    finally:
        files_to_clean = [video_path, audio_path, cover_donor_path]
        for file in files_to_clean:
            if file and os.path.exists(file):
                try:
                    os.remove(file)
                except Exception:
                    pass