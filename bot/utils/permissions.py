from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner

from bot.db import Database

LEVEL_ROOT = "root"
LEVEL_SUDO = "sudoers"
LEVEL_USER = "user"

ADMIN_STATUSES = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}


async def get_member(bot: Bot, chat_id: int, user_id: int):
    try:
        return await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError:
        return None


async def privilege_level(bot: Bot, db: Database, chat_id: int, user_id: int, owner_id: int) -> str:
    if user_id == owner_id:
        return LEVEL_ROOT
    if await db.is_sudo(user_id):
        return LEVEL_SUDO
    member = await get_member(bot, chat_id, user_id)
    if member is None:
        return LEVEL_USER
    if member.status == ChatMemberStatus.CREATOR:
        return LEVEL_ROOT
    if member.status == ChatMemberStatus.ADMINISTRATOR:
        return LEVEL_SUDO
    return LEVEL_USER


async def is_admin(bot: Bot, db: Database, chat_id: int, user_id: int, owner_id: int) -> bool:
    return await privilege_level(bot, db, chat_id, user_id, owner_id) in (LEVEL_ROOT, LEVEL_SUDO)


async def is_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await get_member(bot, chat_id, user_id)
    return member is not None and member.status in ADMIN_STATUSES


async def bot_rights(bot: Bot, chat_id: int) -> ChatMemberAdministrator | ChatMemberOwner | None:
    member = await get_member(bot, chat_id, bot.id)
    if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
        return member
    return None


async def bot_can(bot: Bot, chat_id: int, right: str) -> bool:
    member = await bot_rights(bot, chat_id)
    if member is None:
        return False
    if isinstance(member, ChatMemberOwner):
        return True
    return bool(getattr(member, right, False))


GROUP_TYPES = {ChatType.GROUP.value, ChatType.SUPERGROUP.value}


def is_group(chat_type: str | ChatType | None) -> bool:
    if chat_type is None:
        return False
    value = chat_type.value if isinstance(chat_type, ChatType) else str(chat_type)
    return value in GROUP_TYPES
