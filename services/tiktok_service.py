import os
import asyncio
import aiohttp
from aiogram import types

from services.core.cobalt_engine import fetch_media_from_cobalt
from services.core.ytdlp_engine import download_video_ytdlp, extract_audio_ytdlp, get_media_caption
from services.utils_service import format_caption, is_fake_file, _resolve_short_url, download_temp_file
from services.telegram_sender import send_universal_media
from messages import msgs

async def fetch_tiktok_api(url: str) -> dict | None:
    real_url = await asyncio.to_thread(_resolve_short_url, url)
    api_url = f"https://tikwm.com/api/?url={real_url}"
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 0 and "data" in data:
                        return data["data"]
    except Exception:
        pass
    return None

async def process_tiktok_or_shorts(url: str, message: types.Message, wait_msg: types.Message):
    avatar_path = None
    audio_path = None
    video_path = None
    temp_vid = None

    try:
        # ===============================================================
        # Уровень 1: TIKWM (Оупенсорс сервис, хендлит 90% всех запросов)
        # ===============================================================
        await wait_msg.edit_text(msgs.DOWNLOADING.format(tag="TT"))
        tk_data = await fetch_tiktok_api(url)

        if tk_data:

            caption = format_caption(url, tk_data.get("title", ""))
            avatar_path = None
            author = tk_data.get("author", {})
            avatar_url = author.get("avatar_larger") or author.get("avatar_thumb") or author.get("avatar")
            if avatar_url:
                avatar_path = await download_temp_file(avatar_url)
            audio_url = tk_data.get("music")
            audio_path = None
            if audio_url:
                audio_path = await download_temp_file(audio_url)

            # === Формируем словарь для функции-отправителя ===
            media_data = {
                "caption": caption,
                "avatar_path": avatar_path,
                "audio_path": audio_path if not is_fake_file(audio_path) else None,
                "audio_title": tk_data.get("music_info", {}).get("title", "Original Sound"),
                "audio_performer": tk_data.get("music_info", {}).get("author", "TikTok Audio")
            }

            # === Кейс 1: Карусель (Фотки) ===
            if "images" in tk_data and isinstance(tk_data["images"], list):
                media_data["type"] = "carousel"
                media_data["carousel_items"] = [{"type": "photo", "url": img} for img in tk_data["images"]]

            # === Кейс 2: Видео ===
            elif tk_data.get("play"):
                media_data["type"] = "video"
                temp_vid = await download_temp_file(tk_data["play"])
                media_data["video_path"] = temp_vid if not is_fake_file(temp_vid) else None

            await send_universal_media(message, wait_msg, media_data)
            return

        # ==============================
        # Уровень 2: COBALT (Резерв №1)
        # ==============================
        await wait_msg.edit_text(msgs.DOWNLOADING_SECOND.format(tag="TT"))

        cobalt_data = await fetch_media_from_cobalt(url)

        if cobalt_data:
            original_caption = await get_media_caption(url)
            caption = format_caption(url, original_caption)
            audio_path = None
            if cobalt_data.get("audio_url"):
                audio_path = await download_temp_file(cobalt_data["audio_url"])

            title, performer = "Original Sound", "TikTok Audio"
            if not audio_path or is_fake_file(audio_path):
                safe_url = url.replace("/photo/", "/video/")
                audio_path, title, performer = await extract_audio_ytdlp(safe_url)

            # === Формируем словарь для функции-отправителя ===
            media_data = {
                "caption": caption,
                "audio_path": audio_path if not is_fake_file(audio_path) else None,
                "audio_title": title,
                "audio_performer": performer
            }

            # === Кейс 1: Карусель (Фотки) ===
            if cobalt_data.get("picker"):
                media_data["type"] = "carousel"
                media_data["carousel_items"] = [{"type": item.get("type", "photo"), "url": item["url"]} for item in cobalt_data["picker"]]

            # === Кейс 2: Видео ===
            elif cobalt_data.get("video_url"):
                media_data["type"] = "video"
                temp_vid = await download_temp_file(cobalt_data["video_url"])
                media_data["video_path"] = temp_vid if not is_fake_file(temp_vid) else None

            await send_universal_media(message, wait_msg, media_data)
            return

        # ==============================
        # Уровень 3: YT-DLP (Резерв №2)
        # ==============================
        await wait_msg.edit_text(msgs.DOWNLOADING_THIRD.format(tag="TT"))
        video_path = await download_video_ytdlp(url)

        if video_path and not is_fake_file(video_path):
            original_caption = await get_media_caption(url)
            audio_path, title, performer = await extract_audio_ytdlp(url)

            media_data = {
                "type": "video",
                "video_path": video_path,
                "caption": format_caption(url, original_caption),
                "audio_path": audio_path if not is_fake_file(audio_path) else None,
                "audio_title": title,
                "audio_performer": performer
            }

            await send_universal_media(message, wait_msg, media_data)
        else:
            await wait_msg.edit_text(msgs.TT_DOWNLOAD_FAILED)
            if video_path and os.path.exists(video_path):
                os.remove(video_path)

    finally:
        files_to_clean = [avatar_path, audio_path, video_path, temp_vid]

        for file in files_to_clean:
            if file and os.path.exists(file):
                try:
                    os.remove(file)
                except Exception:
                    pass