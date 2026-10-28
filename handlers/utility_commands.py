import os
import logging
import secrets
from dotenv import load_dotenv
from aiogram.filters import Command, CommandObject
import html
from aiogram import Router, types
from database import database
from messages import msgs

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID"))

router = Router()
logger = logging.getLogger(__name__)

######################################################
################### USER COMMANDS ####################
######################################################

@router.message(lambda msg: (msg.text or msg.caption or "").lower().startswith("@all"))
async def cmd_tag_all(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    members = database.get_all_members(message.chat.id)

    if not members:
        return

    mentions = []
    for user_id, full_name in members:
        safe_name = html.escape(full_name)
        mentions.append(f'<a href="tg://user?id={user_id}">{safe_name}</a>')

    mentions_text = ", ".join(mentions)
    try:
        await message.reply(mentions_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"{msgs.TAG_ALL_SEND_ERR}: {e}")



######################################################
################### ADMIN COMMANDS ###################
######################################################

####################### KEYS #########################

@router.message(Command("newkey", "genkey", "nk", "gk"))
async def cmd_generate_key(message: types.Message, command: CommandObject):
    """
    Генерирует новый уникальный и одноразовый ключ активации бота в ЛС либо в группе.
    """
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    else:
        new_key = f"FLU_{secrets.token_hex(8)}"
        note = command.args.strip() if command.args else None
        database.add_key(new_key, note)
        await message.reply(msgs.NEW_KEY_GENERATED.format(key=new_key), parse_mode="HTML")

@router.message(Command("timeout", "out"))
async def cmd_timeout_key(message: types.Message, command: CommandObject):
    """
    Деактивирует ключ.
    В БД остается запись о ключе, но его больше нельзя использовать,
    а бот становится более недоступным в группе/чате,
    в которой он был активирован этим ключом.
    """
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    if not command.args:
        await message.reply(msgs.TIMEOUT_USAGE, parse_mode="HTML")
        return

    key_to_timeout = command.args.strip()
    success = database.timeout_key(key_to_timeout)

    if success:
        await message.reply(msgs.KEY_TIMED_OUT.format(key=key_to_timeout), parse_mode="HTML")
    else:
        await message.reply(msgs.KEY_NOT_FOUND)



@router.message(Command("revive", "rev"))
async def cmd_revive_key(message: types.Message, command: CommandObject):
    """
    Возобновляет ключ.
    В группе, к которой приписан токен, бот становится вновь доступным.
    """
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    if not command.args:
        await message.reply(msgs.REVIVE_USAGE, parse_mode="HTML")
        return

    key_to_revive = command.args.strip()
    success = database.revive_key(key_to_revive)

    if success:
        await message.reply(msgs.KEY_REVIVED.format(key=key_to_revive), parse_mode="HTML")
    else:
        await message.reply(msgs.KEY_NOT_FOUND)

def format_keys_list(keys: list, title: str) -> str:
    """
    Вспомогательная функция для вывода списка ключей
    """
    if not keys:
        return msgs.KEYS_EMPTY.format(title=title)

    text = f"{title}\n\n"
    for key, is_active, username, used_by_user_id, activated_at, info in keys:
        if is_active == 1:
            status = msgs.KEY_STATUS_FREE
        elif is_active == 0:
            status = msgs.KEY_STATUS_ACTIVE.format(chat_id=used_by_user_id, username=username)
        else:  # is_active == -1
            status = msgs.KEY_STATUS_REVOKED.format(chat_id=used_by_user_id, username=username)

        note = f"📝 <i>{info}</i>" if info else f"📝 <i>{msgs.KEY_NO_NOTE}</i>"
        time_str = f"🕒 <i>{activated_at}</i>" if activated_at else ""

        text += f"🔑 <code>{key}</code>\n"
        text += f"📌 Статус: {status}\n"
        text += f"{note}\n"
        if time_str:
            text += f"{time_str}\n"
        text += "+—————————————+\n"

    if len(text) > 4000:
        text = text[:4000] + msgs.KEYS_LIST_TRUNCATED
    return text

@router.message(Command("keys"))
async def cmd_keys(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    keys = database.get_all_keys("active")
    await message.reply(format_keys_list(keys, msgs.KEYS_TITLE), parse_mode="HTML")

@router.message(Command("deadkeys"))
async def cmd_deadkeys(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    keys = database.get_all_keys("dead")
    await message.reply(format_keys_list(keys, msgs.DEADKEYS_TITLE), parse_mode="HTML")

@router.message(Command("ids"))
async def cmd_get_ids(message: types.Message):
    """
    Выводит ID юзера, ID чата (если это ЛС, то ID юзера = ID чата) и тип чата.
    """
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    else:
        chat_id = message.chat.id
        chat_type = message.chat.type
        text = msgs.IDS_INFO.format(user_id=user_id, chat_id=chat_id, chat_type=chat_type)

        await message.reply(text, parse_mode="HTML")