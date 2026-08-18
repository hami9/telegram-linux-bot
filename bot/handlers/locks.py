from __future__ import annotations

from aiogram.enums import MessageEntityType
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.constants import LOCK_TYPES
from bot.db import Database
from bot.filters import IsGroup
from bot.i18n import t
from bot.utils.formatting import clean
from bot.utils.parsing import split_command_args
from bot.utils.permissions import bot_can, is_admin, is_chat_admin

router = Router(name="locks")
router.message.filter(IsGroup())

LINK_ENTITIES = {MessageEntityType.URL, MessageEntityType.TEXT_LINK}


async def _require_admin(message: Message, db: Database, settings: Settings, lang: str) -> bool:
    if message.from_user is None:
        return False
    if await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
        return True
    await message.reply(t("common.no_permission", lang))
    return False


@router.message(Command("lock"))
async def cmd_lock(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    lock_type = args[0].lower() if args else ""
    if lock_type not in LOCK_TYPES:
        await message.reply(t("locks.invalid", lang, types=", ".join(LOCK_TYPES)))
        return
    await db.set_lock(message.chat.id, lock_type, True)
    await message.reply(t("locks.locked", lang, type=clean(lock_type)))


@router.message(Command("unlock"))
async def cmd_unlock(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    lock_type = args[0].lower() if args else ""
    if lock_type not in LOCK_TYPES:
        await message.reply(t("locks.invalid", lang, types=", ".join(LOCK_TYPES)))
        return
    await db.set_lock(message.chat.id, lock_type, False)
    await message.reply(t("locks.unlocked", lang, type=clean(lock_type)))


@router.message(Command("locks", "locklist"))
async def cmd_locks(message: Message, lang: str, db: Database) -> None:
    locked = await db.get_locks(message.chat.id)
    if not locked:
        await message.reply(t("locks.none", lang))
        return
    listed = "\n".join(f"🔒 <code>{clean(item)}</code>" for item in sorted(locked))
    await message.reply(f"{t('locks.list_title', lang)}\n{listed}")


def violated_locks(message: Message, locked: set[str]) -> str | None:
    if not locked:
        return None
    entities = list(message.entities or []) + list(message.caption_entities or [])

    if "link" in locked and any(entity.type in LINK_ENTITIES for entity in entities):
        return "link"
    if "mention" in locked and any(
        entity.type in {MessageEntityType.MENTION, MessageEntityType.TEXT_MENTION} for entity in entities
    ):
        return "mention"
    if "forward" in locked and message.forward_origin is not None:
        return "forward"
    if "photo" in locked and message.photo:
        return "photo"
    if "video" in locked and (message.video or message.video_note):
        return "video"
    if "sticker" in locked and message.sticker:
        return "sticker"
    if "gif" in locked and message.animation:
        return "gif"
    if "voice" in locked and (message.voice or message.audio):
        return "voice"
    if "document" in locked and message.document:
        return "document"
    if "media" in locked and any(
        (
            message.photo,
            message.video,
            message.animation,
            message.document,
            message.sticker,
            message.voice,
            message.audio,
            message.video_note,
        )
    ):
        return "media"
    return None


async def enforce_locks(message: Message, db: Database) -> bool:
    if message.from_user is None:
        return False
    locked = await db.get_locks(message.chat.id)
    if not locked:
        return False
    if await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        return False
    if violated_locks(message, locked) is None:
        return False
    if not await bot_can(message.bot, message.chat.id, "can_delete_messages"):
        return False
    try:
        await message.delete()
    except TelegramAPIError:
        return False
    return True


async def enforce_bot_lock(message: Message, db: Database) -> bool:
    if not message.new_chat_members:
        return False
    locked = await db.get_locks(message.chat.id)
    if "bots" not in locked:
        return False
    if not await bot_can(message.bot, message.chat.id, "can_restrict_members"):
        return False
    removed = False
    for member in message.new_chat_members:
        if not member.is_bot or member.id == message.bot.id:
            continue
        try:
            await message.bot.ban_chat_member(message.chat.id, member.id)
            removed = True
        except TelegramAPIError:
            continue
    return removed
