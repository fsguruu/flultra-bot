import re

# =======================
# РЕГУЛЯРКИ ДЛЯ СОЦСЕТЕЙ
# =======================
TIKTOK_PATTERN = re.compile(r"^https?://(www\.)?(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)/.*")

INSTAGRAM_PATTERN = re.compile(r"^https?://(www\.)?instagram\.com/([^/]+/)?(reels?|p|audio)/.*")

YOUTUBE_SHORTS_PATTERN = re.compile(r"^https?://(www\.)?youtube\.com/shorts/.*")


def identify_media_network(url: str) -> str | None:
    """
    Перевіряє URL і повертає назву соцмережі, якщо посилання дозволене.
    Якщо посилання нам не підходить (наприклад, довге відео з Ютубу) - повертає None.
    """
    url = url.strip()

    if TIKTOK_PATTERN.match(url):
        return "tiktok"

    if INSTAGRAM_PATTERN.match(url):
        return "instagram"

    if YOUTUBE_SHORTS_PATTERN.match(url):
        return "youtube_shorts"

    return None