from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, ChatPermissions, Message

from bot.constants import (
    BOT_RIGHTS,
    MEMBER_PERMISSIONS,
    RIGHT_SOURCES,
    ROLE_ADMIN,
    ROLE_MEMBER,
    ROLE_OWNER,
)
from bot.db import Database
from bot.i18n import t
from bot.utils.permissions import get_member, is_group


def default_rights(member: ChatMemberAdministrator | ChatMemberOwner | None) -> dict[str, bool]:
    if isinstance(member, ChatMemberOwner):
        return {right: True for right in BOT_RIGHTS}
    if member is None:
        return {right: False for right in BOT_RIGHTS}
    rights: dict[str, bool] = {}
    for right in BOT_RIGHTS:
        source = RIGHT_SOURCES.get(right, "")
        if source == "never":
            rights[right] = False
        elif source:
            rights[right] = bool(getattr(member, source, False))
        else:
            rights[right] = True
    return rights


async def resolve_role(bot: Bot, db: Database, chat_id: int, user_id: int, owner_id: int) -> str:
    if user_id == owner_id or await db.is_sudo(user_id):
        return ROLE_OWNER
    member = await get_member(bot, chat_id, user_id)
    if member is None:
        return await db.get_role(chat_id, user_id) or ROLE_MEMBER
    if member.status == ChatMemberStatus.CREATOR:
        return ROLE_OWNER
    if member.status == ChatMemberStatus.ADMINISTRATOR:
        return ROLE_ADMIN
    return ROLE_MEMBER


async def effective_rights(
    bot: Bot, db: Database, chat_id: int, user_id: int, owner_id: int
) -> dict[str, bool]:
    if user_id == owner_id or await db.is_sudo(user_id):
        return {right: True for right in BOT_RIGHTS}

    member = await get_member(bot, chat_id, user_id)
    if isinstance(member, ChatMemberOwner):
        return {right: True for right in BOT_RIGHTS}
    if not isinstance(member, ChatMemberAdministrator):
        return {right: False for right in BOT_RIGHTS}

    rights = default_rights(member)
    for right, value in (await db.get_overrides(chat_id, user_id)).items():
        if right in rights:
            rights[right] = value
    return rights


async def require_right(message: Message, db: Database, settings, lang: str, right: str) -> bool:
    if message.from_user is None or message.chat is None:
        return False
    if not is_group(message.chat.type):
        return True
    rights = await effective_rights(
        message.bot, db, message.chat.id, message.from_user.id, settings.owner_id
    )
    if rights.get(right, False):
        return True
    if any(rights.values()):
        await message.reply(t("roles.no_right", lang, right=t(f"roles.right_{right}", lang)))
    else:
        await message.reply(t("common.no_permission", lang))
    return False


async def sync_staff(bot: Bot, db: Database, chat_id: int) -> tuple[int, int]:
    try:
        members = await bot.get_chat_administrators(chat_id)
    except TelegramAPIError:
        return -1, -1

    staff: dict[int, str] = {}
    owners = 0
    admins = 0
    for member in members:
        if member.user.is_bot:
            continue
        await db.remember_user(member.user.id, member.user.full_name, member.user.username or "")
        if member.status == ChatMemberStatus.CREATOR:
            staff[member.user.id] = ROLE_OWNER
            owners += 1
        else:
            staff[member.user.id] = ROLE_ADMIN
            admins += 1

    await db.replace_staff(chat_id, staff)
    return owners, admins


def current_member_permissions(member) -> dict[str, bool]:
    allowed: dict[str, bool] = {}
    for name, fields in MEMBER_PERMISSIONS.items():
        if member is None:
            allowed[name] = True
            continue
        values = [getattr(member, field, None) for field in fields]
        known = [bool(value) for value in values if value is not None]
        allowed[name] = all(known) if known else member.status != ChatMemberStatus.RESTRICTED
    return allowed


def build_permissions(allowed: dict[str, bool]) -> ChatPermissions:
    payload: dict[str, bool] = {}
    for name, fields in MEMBER_PERMISSIONS.items():
        for field in fields:
            payload[field] = bool(allowed.get(name, True))
    payload["can_send_messages"] = bool(allowed.get("messages", True))
    return ChatPermissions(**payload)
