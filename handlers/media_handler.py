import re
import logging
from aiogram import Router, types
from services.instagram_service import process_instagram
from services.tiktok_service import process_tiktok_or_shorts
from services.url_validator import identify_media_network
from messages import msgs

router = Router()
logger = logging.getLogger(__name__)


def extract_url(text: str) -> str | None:
    """ Вытягивает первую попавшуюся ссылку из текста """
    match = re.search(r'(https?://[^\s]+)', text)
    return match.group(0) if match else None


@router.message()
async def handle_media_link(message: types.Message):
    text = message.text or message.caption or ""
    url = extract_url(text)

    if not url:
        return

    network = identify_media_network(url)

    if not network:
        return

    logger.info(f"[TIMING] link received: {network}")
    wait_msg = await message.answer(msgs.ANALYZING_LINK)

    try:
        if network == "instagram":
            await process_instagram(url, message, wait_msg)

        elif network in ["tiktok", "youtube_shorts"]:
            await process_tiktok_or_shorts(url, message, wait_msg)

    except Exception as e:
        await wait_msg.edit_text(msgs.CRITICAL_PROCESSING_ERR)
        logger.exception(f"Ошибка хендлера: {e}")