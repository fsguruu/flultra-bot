import os
import logging
import uuid
import aiohttp
import asyncio
import shutil
import urllib.request
from PIL import Image
from messages import msgs

logger = logging.getLogger(__name__)

def format_caption(url: str, original_caption: str) -> str:
    """Форматирование описания под сообщением бота."""
    if original_caption and len(original_caption) > 250:
        original_caption = original_caption[:250] + msgs.CAPTION_TRUNCATED_SUFFIX

    final_caption = f"{msgs.CAPTION_HEADER.format(url=url)}\n{original_caption}"
    return final_caption

def is_fake_file(path: str) -> bool:
    """Проверка, не является ли файл битым HTML."""
    if not path or not os.path.exists(path):
        return True
    if os.path.getsize(path) < 500:
        return True
    try:
        with open(path, 'rb') as f:
            head = f.read(50).lower()
            if b'<!doctype' in head or b'<html' in head or b'{"status"' in head or b'error' in head:
                return True
    except Exception:
        pass
    return False

def _resolve_short_url(url: str) -> str:
    """Раскрывает короткие ссылки (наприм. yt.be либо vt.tiktok)."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.geturl()
    except Exception:
        return url

async def download_temp_file(url: str) -> str | None:
    """Качает файл, явно указывая расширение."""
    os.makedirs("downloads", exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    if "image" in content_type:
                        ext = "jpg"
                    elif "audio" in content_type:
                        ext = "mp3"
                    else:
                        ext = "mp4"
                    filename = f"downloads/temp_{uuid.uuid4().hex}.{ext}"
                    with open(filename, 'wb') as f:
                        while True:
                            chunk = await resp.content.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                    return filename
                else:
                    logger.error(f"❌ Ошибка загрузки: {resp.status} URL: {url}")
                    return None
    except Exception as e:
        logger.error(f"❌ Ошибка временного файла: {e}")
        return None

async def create_square_thumbnail(audio_path: str = None, video_path: str = None, avatar_path: str = None) -> str | None:
    """Создает обложку для отдельного звука с видео."""
    ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
    raw_cover = f"downloads/raw_cover_{uuid.uuid4().hex}.jpg"
    try:
        if avatar_path and os.path.exists(avatar_path): shutil.copy2(avatar_path, raw_cover)
        elif audio_path and os.path.exists(audio_path):
            proc = await asyncio.create_subprocess_exec(ffmpeg_path, "-y", "-i", audio_path, "-an", "-vcodec", "copy", raw_cover, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await proc.communicate()
        if not os.path.exists(raw_cover) and video_path and os.path.exists(video_path):
            proc = await asyncio.create_subprocess_exec(ffmpeg_path, "-y", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", raw_cover, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await proc.communicate()
        if os.path.exists(raw_cover):
            square_cover = raw_cover + "_sq.jpg"
            with Image.open(raw_cover) as img:
                if img.mode != 'RGB': img = img.convert('RGB')
                w, h = img.size
                min_dim = min(w, h)
                img = img.crop(((w - min_dim) // 2, (h - min_dim) // 2, (w + min_dim) // 2, (h + min_dim) // 2))
                img.thumbnail((320, 320))
                img.save(square_cover, format="JPEG", quality=90)
            os.remove(raw_cover)
            return square_cover
    except Exception: pass
    return None

async def embed_cover_into_audio(audio_path: str, cover_path: str) -> str | None:
    """Вшивает картинку в MP3"""
    ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
    final_mp3 = audio_path + "_embedded.mp3"

    try:
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_path, "-y",
            "-i", audio_path,
            "-i", cover_path,
            "-map", "0:a:0",
            "-map", "1:v:0",
            "-c:a", "libmp3lame", "-q:a", "2",
            "-c:v", "mjpeg",
            "-id3v2_version", "3",
            final_mp3,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()

        if os.path.exists(final_mp3) and os.path.getsize(final_mp3) > 0:
            return final_mp3
    except Exception:
        pass
    return None