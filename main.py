import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from database import database
from messages import msgs, IS_LOCAL

# Services
from services.cleanup_service import auto_clean_downloads

# Middlewares
from middlewares import middleware
from middlewares.outer_middleware import OldMessagesFilterMiddleware

# Handlers
from handlers import auth_user, utility_commands, media_handler

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

dp.message.middleware(middleware.UserTrackerMiddleware())
dp.message.middleware(middleware.AuthMiddleware())
dp.message.outer_middleware(OldMessagesFilterMiddleware())

dp.include_router(utility_commands.router)
if IS_LOCAL:
    # Fun commands exist only in local mode
    from handlers import fun_commands
    dp.include_router(fun_commands.router)
dp.include_router(auth_user.router)
dp.include_router(media_handler.router)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.reply(msgs.START_RESPONSE, parse_mode="HTML")

async def main():
    logging.info(f"Бот запущений і готовий до роботи! Режим: {'local' if IS_LOCAL else 'prod'}")
    database.init_db()

    asyncio.create_task(auto_clean_downloads(
        folder="downloads",
        max_age_minutes=30,
        check_interval_minutes=15
    ))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())