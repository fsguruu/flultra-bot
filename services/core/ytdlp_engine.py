import yt_dlp
import os
import asyncio
import logging
import aiohttp
import re
import html as pyhtml

logger = logging.getLogger(__name__)
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

BYPASS_OPTS = {
    'source_address': '0.0.0.0',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
}

# ==========================================
# ВІДЕО ЗАВАНТАЖУВАЧ
# ==========================================
def sync_download_video(url: str) -> str | None:
    logger.info(f"Качаю видос: {url}")
    downloads_dir = "downloads"
    os.makedirs(downloads_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{downloads_dir}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 10,
        'max_filesize': 50 * 1024 * 1024,
        'merge_output_format': 'mp4',
        'postprocessor_args': ['-movflags', '+faststart'],
        'ffmpeg_location': FFMPEG_PATH,
    }
    ydl_opts.update(BYPASS_OPTS)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if not filename.endswith('.mp4'):
                filename = filename.rsplit('.', 1)[0] + '.mp4'

            return filename
    except Exception as e:
        logger.error(f"yt-dlp не смог скачать видео: {e}")
        return None

# ==========================================
# АУДІО ЗАВАНТАЖУВАЧ
# ==========================================
async def extract_audio_ytdlp(url: str) -> tuple[str | None, str | None, str | None]:
    ydl_opts_info = {
        'quiet': True,
        'no_warnings': True,
    }
    ydl_opts_info.update(BYPASS_OPTS)

    ydl_opts_download = {
        'format': 'bestaudio/best',
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            {'key': 'FFmpegMetadata', 'add_metadata': True},
            {'key': 'EmbedThumbnail'},
        ],
        'outtmpl': 'downloads/audio_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH,
    }
    ydl_opts_download.update(BYPASS_OPTS)

    try:
        loop = asyncio.get_event_loop()

        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            duration = info.get('duration', 0)

            if duration > 60:
                logger.info(f"Відео занадто довге ({duration} сек).")
                return None, None, None

            track_title = info.get('track') or info.get('title') or "Оригінальний звук"
            track_performer = info.get('artist') or info.get('uploader') or "Невідомий автор"

        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp3_path = f"{base}.mp3"

            if os.path.exists(mp3_path):
                return mp3_path, track_title, track_performer
            return None, None, None

    except Exception as e:
        logger.error(f"Ошибка при попытке достать звук: {e}")
        return None, None, None

# ==========================================
# ПАРСЕР ОПИСУ ДЛЯ ІНСТИ (OpenGraph)
# ==========================================
async def fetch_caption_from_opengraph(url: str) -> str:
    """Instagram віддає og:-теги без логіну, якщо User-Agent - краулер Facebook."""
    headers = {
        "User-Agent": "facebookexternalhit/1.1"
    }
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html_text = await response.text()

                    # 1. Шукаємо og:description (Основний опис, підтримує переноси рядків \n)
                    match_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html_text)
                    if not match_desc:
                        match_desc = re.search(r'<meta\s+content="([^"]+)"\s+property="og:description"', html_text)

                    if match_desc:
                        # Декодуємо HTML-сутності (наприклад, &#10; перетвориться на справжній Enter)
                        return pyhtml.unescape(match_desc.group(1)).strip()

                    # 2. Резерв: og:title (Там текст у форматі 'Ім'я on Instagram: "Опис"')
                    match_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_text)
                    if not match_title:
                        match_title = re.search(r'<meta\s+content="([^"]+)"\s+property="og:title"', html_text)

                    if match_title:
                        raw_title = pyhtml.unescape(match_title.group(1))
                        if 'on Instagram: "' in raw_title:
                            caption = raw_title.split('on Instagram: "', 1)[-1]
                            if caption.endswith('"'):
                                caption = caption[:-1]
                            return caption.strip()
                        return raw_title.strip()
    except Exception as e:
        logger.error(f"❌ [OPENGRAPH PARSER] Ошибка: {e}")

    return ""

# ==========================================
# ГОЛОВНИЙ ПАРСЕР ОПИСУ (Капшн)
# ==========================================
async def get_media_caption(url: str) -> str:
    """Витягує опис посту без завантаження медіа."""

    # Пріоритет 1: Instagram через OpenGraph
    if "instagram.com" in url:
        caption = await fetch_caption_from_opengraph(url)
        if caption:
            return caption

    # Пріоритет 2: yt-dlp
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    ydl_opts.update(BYPASS_OPTS)

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            caption = info.get('description') or info.get('title') or ""

            if not caption and 'entries' in info and info['entries']:
                first_entry = info['entries'][0]
                if isinstance(first_entry, dict):
                    caption = first_entry.get('description') or first_entry.get('title') or ""

            if caption:
                return caption.strip()

    except Exception as e:
        logger.warning(f"yt-dlp не зміг витягнути опис: {e}")

    return ""

async def download_video_ytdlp(url: str) -> str | None:
    return await asyncio.to_thread(sync_download_video, url)