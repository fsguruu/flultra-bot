import os
from aiogram import Router, types
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import database
from messages import msgs

router = Router()
ADMIN_ID = int(os.getenv("ADMIN_ID"))

class LoginState(StatesGroup):
    waiting_for_token = State()

@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply(msgs.SLASH_CANCEL_RESPONSE)

@router.message(Command("login"), StateFilter("*"))
async def cmd_login_one_step(message: types.Message, command: CommandObject, state: FSMContext):
    if command.args:
        await process_login_logic(command.args, message, state)
        return
    await message.reply(msgs.WAITING_FOR_KEY_STATE)
    await state.set_state(LoginState.waiting_for_token)

@router.message(LoginState.waiting_for_token)
async def clean_login_state(message: types.Message, state: FSMContext):
    await process_login_logic(message.text, message, state)

async def is_group_admin(message: types.Message) -> bool:
    if message.from_user.id == ADMIN_ID:
        return True
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)

async def process_login_logic(token: str, message: types.Message, state: FSMContext):
    user_token = (token or "").strip()
    chat_id = message.chat.id
    is_group = message.chat.type in ["group", "supergroup"]

    # In groups only chat admins may activate the bot
    if is_group and not await is_group_admin(message):
        await message.reply(msgs.LOGIN_ADMINS_ONLY)
        await state.clear()
        return

    is_valid = database.check_key(user_token)

    if is_valid:
        raw_username = message.from_user.username
        username = f"@{raw_username}" if raw_username else message.from_user.first_name
        database.use_key(user_token, chat_id, username)
        if is_group:
            await message.reply(msgs.GROUP_REGISTERED_SUCCESS)
        else:
            await message.reply(msgs.PRIVATE_REGISTERED_SUCCESS)
        await state.clear()
    else:
        await message.reply(msgs.INVALID_KEY)