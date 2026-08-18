from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.constants import PUNISH_MODES
from bot.db import Database
from bot.filters import IsGroup
from bot.handlers.admin import punish
from bot.i18n import t
from bot.services.ratelimit import FloodTracker
from bot.utils.formatting import mention
from bot.utils.parsing import split_command_args
from bot.utils.permissions import bot_can, is_admin, is_chat_admin

router = Router(name="antiflood")
router.message.filter(IsGroup())

tracker = FloodTracker()


async def _require_admin(message: Message, db: Database, settings: Settings, lang: str) -> bool:
    if message.from_user is None:
        return False
    if await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
        return True
    await message.reply(t("common.no_permission", lang))
    return False


@router.message(Command("antiflood", "flood"))
async def cmd_antiflood(message: Message, lang: str, db: Database) -> None:
    chat = await db.get_chat(message.chat.id)
    limit = t("common.off", lang) if chat.flood_limit <= 0 else str(chat.flood_limit)
    await message.reply(t("antiflood.status", lang, limit=limit, mode=chat.flood_mode))


@router.message(Command("setflood"))
async def cmd_setflood(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    value = args[0].lower() if args else ""
    if value in {"off", "0", "no", "disable"}:
        await db.set_chat_field(message.chat.id, "flood_limit", 0)
        await message.reply(t("antiflood.off", lang))
        return
    if not value.isdigit() or not 3 <= int(value) <= 50:
        await message.reply(t("antiflood.invalid", lang))
        return
    await db.set_chat_field(message.chat.id, "flood_limit", int(value))
    await message.reply(t("antiflood.set", lang, limit=int(value)))


@router.message(Command("setfloodmode", "floodmode"))
async def cmd_setfloodmode(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    mode = args[0].lower() if args else ""
    if mode not in PUNISH_MODES:
        await message.reply(t("warns.mode_invalid", lang))
        return
    await db.set_chat_field(message.chat.id, "flood_mode", mode)
    await message.reply(t("antiflood.mode_set", lang, mode=mode))


async def enforce_antiflood(message: Message, db: Database, lang: str) -> bool:
    if message.from_user is None or message.from_user.is_bot:
        return False
    chat = await db.get_chat(message.chat.id)
    if chat.flood_limit <= 0:
        return False
    if not tracker.hit(message.chat.id, message.from_user.id, chat.flood_limit):
        return False
    if await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        return False
    if not await bot_can(message.bot, message.chat.id, "can_restrict_members"):
        return False
    if not await punish(message.bot, message.chat.id, message.from_user.id, chat.flood_mode):
        return False
    await message.answer(
        t("antiflood.triggered", lang, user=mention(message.from_user), action=chat.flood_mode)
    )
    return True
