import os
import logging
from aiogram import types
from aiogram.types import FSInputFile
from aiogram.utils.media_group import MediaGroupBuilder
from services.utils_service import create_square_thumbnail, embed_cover_into_audio
import aiohttp
from aiogram.types import BufferedInputFile
import asyncio
from messages import msgs

logger = logging.getLogger(__name__)


async def download_media_to_memory(url: str, filename: str = "media.jpg") -> BufferedInputFile | None:
    """
    Качає файл в оперативну пам'ять, маскуючись під реальний браузер.
    """
    # Браузерні заголовки, інакше CDN TikTok/Instagram віддає 403
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.tiktok.com/"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    file_bytes = await resp.read()
                    return BufferedInputFile(file_bytes, filename=filename)
                else:
                    logger.error(f"❌ Ошибка скачивания: {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файла в память: {e}")
        return None

async def send_universal_media(message: types.Message, wait_msg: types.Message, media_data: dict):
    """
    Универсальная функция для отправки медиа.
    media_data ожидает такой формат:
    {
        "type": "video" либо "carousel",
        "video_path": "путь" (если видео),
        "carousel_items": [{"type": "photo", "url": "..."}] (если карусель),
        "caption": "Текст...",
        "audio_path": "путь" (если есть аудіо),
        "avatar_path": "шлях" (если есть аватарка),
        "audio_title": "Название",
        "audio_performer": "Автор"
    }
    """
    try:
        # 1. ВІДПРАВКА ОДИНОЧНОГО МЕДІА (Відео або Фото)
        file_path = media_data.get("video_path")
        media_type = media_data.get("type")

        if file_path and media_type in ["video", "photo"]:
            if file_path.endswith((".jpg", ".jpeg", ".png", ".webp")):
                await message.reply_photo(
                    photo=FSInputFile(file_path),
                    caption=media_data.get("caption", ""),
                    parse_mode="HTML"
                )
            else:
                await message.reply_video(
                    video=FSInputFile(file_path, filename="video.mp4"),
                    caption=media_data.get("caption", ""),
                    parse_mode="HTML",
                    supports_streaming=True
                )

        # 2. ОТПРАВКА КАРУСЕЛИ
        elif media_data.get("type") == "carousel" and media_data.get("carousel_items"):
            items = media_data["carousel_items"]
            chunks = [items[i:i + 10] for i in range(0, len(items), 10)]

            for chunk_idx, chunk in enumerate(chunks):
                album = MediaGroupBuilder()
                for i, item in enumerate(chunk):
                    cap = media_data.get("caption", "") if (chunk_idx == 0 and i == 0) else None

                    ext = "video.mp4" if item.get("type") == "video" else f"image_{i}.jpg"

                    safe_media = await download_media_to_memory(item["url"], filename=ext)

                    if safe_media:
                        if item.get("type") == "video":
                            album.add_video(media=safe_media, caption=cap, parse_mode="HTML")
                        else:
                            album.add_photo(media=safe_media, caption=cap, parse_mode="HTML")
                    else:
                        logger.warning(f"Пропущено слайд каруселі через блокування: {item['url']}")

                built_album = album.build()
                if built_album:
                    await message.reply_media_group(media=built_album)
                else:
                    await message.reply(msgs.CAROUSEL_ALL_FAILED)


        # 3. ОТПРАВКА АУДИО (С обложкой)
        audio_path = media_data.get("audio_path")
        if audio_path and os.path.exists(audio_path):
            # Создание обложки
            sq_cover = await create_square_thumbnail(
                audio_path=audio_path,
                video_path=media_data.get("video_path"),
                avatar_path=media_data.get("avatar_path")
            )

            audio_to_send = audio_path
            if sq_cover and os.path.exists(sq_cover):
                embedded = await embed_cover_into_audio(audio_path, sq_cover)
                if embedded:
                    audio_to_send = embedded

            thumb_file = FSInputFile(sq_cover) if sq_cover else None
            await message.reply_audio(
                audio=FSInputFile(audio_to_send),
                title=media_data.get("audio_title", "Original Sound"),
                performer=media_data.get("audio_performer", "Author"),
                thumbnail=thumb_file
            )

            # Чистимо сміття аудіо
            if os.path.exists(audio_to_send):
                os.remove(audio_to_send)
            if audio_to_send != audio_path and os.path.exists(audio_path): os.remove(audio_path)
            if sq_cover and os.path.exists(sq_cover): os.remove(sq_cover)
        logger.info("[TIMING] sent")

    except Exception as e:
        logger.error(f"❌ [SENDER] Ошибка отправки: {e}")
        await wait_msg.edit_text(msgs.SEND_FAILED)
    finally:
        # Удаление видео и аватарки
        video_path = media_data.get("video_path")
        avatar_path = media_data.get("avatar_path")
        if video_path and os.path.exists(video_path): os.remove(video_path)
        if avatar_path and os.path.exists(avatar_path): os.remove(avatar_path)

        try:
            await asyncio.sleep(10)
            await wait_msg.delete()
        except Exception:
            pass