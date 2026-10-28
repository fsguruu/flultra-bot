from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from database import database
import os
import logging
from dotenv import load_dotenv

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID"))
logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:

        if not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        chat_id = event.chat.id
        text = event.text or ""

        if user_id == ADMIN_ID:
            return await handler(event, data)

        if text.startswith(("/start", "/login", "/cancel")):
            return await handler(event, data)

        state = data.get("state")
        current_state = await state.get_state() if state else None
        if current_state == "LoginState:waiting_for_token":
            return await handler(event, data)

        is_authorized = database.is_chat_authorized(chat_id)

        if is_authorized:
            return await handler(event, data)
        else:
            return


class UserTrackerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):

        if not isinstance(event, Message):
            return await handler(event, data)

        if event.chat.type not in ["group", "supergroup"] or not event.from_user:
            return await handler(event, data)

        # ==========================================
        # Сохранение данных
        # ==========================================
        try:
            chat_id = event.chat.id
            user_id = event.from_user.id
            full_name = event.from_user.full_name

            raw_username = event.from_user.username
            username = f"@{raw_username}" if raw_username else full_name

            database.add_member(chat_id, user_id, full_name, username)

        except Exception as e:
            logger.error(f"❌ Помилка в UserTrackerMiddleware: {e}")

        return await handler(event, data)