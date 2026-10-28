from datetime import datetime, timezone
from aiogram import BaseMiddleware
from aiogram.types import Message
import logging

logger = logging.getLogger(__name__)


class OldMessagesFilterMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        if not isinstance(event, Message):
            return await handler(event, data)
        msg_time = event.date
        now = datetime.now(timezone.utc)
        time_diff = (now - msg_time).total_seconds()
        if time_diff > 60:
            return
        return await handler(event, data)