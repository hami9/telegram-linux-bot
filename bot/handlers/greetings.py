from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.db import Database
from bot.filters import IsGroup
from bot.handlers.locks import enforce_bot_lock
from bot.i18n import t
from bot.utils.formatting import render_template
from bot.utils.parsing import command_payload, split_command_args
from bot.utils.permissions import bot_can, is_admin

router = Router(name="greetings")
router.message.filter(IsGroup())

ON_VALUES = {"on", "yes", "true", "enable", "1"}
OFF_VALUES = {"off", "no", "false", "disable", "0"}


async def _require_admin(message: Message, db: Database, settings: Settings, lang: str) -> bool:
    if message.from_user is None:
        return False
    if await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
        return True
    await message.reply(t("common.no_permission", lang))
    return False


def _switch(args: list[str]) -> bool | None:
    if not args:
        return None
    value = args[0].lower()
    if value in ON_VALUES:
        return True
    if value in OFF_VALUES:
        return False
    return None


async def _toggle(message: Message, lang: str, db: Database, field: str, key: str) -> None:
    args = split_command_args(message.text or "")
    state = _switch(args)
    if state is None:
        chat = await db.get_chat(message.chat.id)
        state = not bool(getattr(chat, field))
    await db.set_chat_field(message.chat.id, field, state)
    label = t("common.enabled", lang) if state else t("common.disabled", lang)
    await message.reply(t(key, lang, state=label))


@router.message(Command("welcome"))
async def cmd_welcome(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    await _toggle(message, lang, db, "welcome_on", "greetings.welcome_state")


@router.message(Command("goodbye"))
async def cmd_goodbye(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    await _toggle(message, lang, db, "goodbye_on", "greetings.goodbye_state")


@router.message(Command("cleanservice"))
async def cmd_cleanservice(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    await _toggle(message, lang, db, "cleanservice", "greetings.cleanservice_state")


@router.message(Command("setwelcome"))
async def cmd_setwelcome(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    text = command_payload(message.text or "")
    if not text and message.reply_to_message is not None:
        text = message.reply_to_message.html_text if message.reply_to_message.text else ""
    if not text:
        await message.reply(t("greetings.need_text", lang))
        return
    await db.set_chat_field(message.chat.id, "welcome_text", text)
    await db.set_chat_field(message.chat.id, "welcome_on", True)
    await message.reply(t("greetings.welcome_set", lang))


@router.message(Command("setgoodbye"))
async def cmd_setgoodbye(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    text = command_payload(message.text or "")
    if not text and message.reply_to_message is not None:
        text = message.reply_to_message.html_text if message.reply_to_message.text else ""
    if not text:
        await message.reply(t("greetings.need_text", lang))
        return
    await db.set_chat_field(message.chat.id, "goodbye_text", text)
    await db.set_chat_field(message.chat.id, "goodbye_on", True)
    await message.reply(t("greetings.goodbye_set", lang))


@router.message(F.new_chat_members)
async def on_join(message: Message, lang: str, db: Database) -> None:
    await enforce_bot_lock(message, db)
    chat = await db.get_chat(message.chat.id)

    if chat.welcome_on:
        template = chat.welcome_text or t("greetings.default_welcome", lang)
        for member in message.new_chat_members or []:
            if member.id == message.bot.id:
                continue
            try:
                await message.answer(render_template(template, user=member, chat=message.chat))
            except TelegramAPIError:
                continue

    if chat.cleanservice and await bot_can(message.bot, message.chat.id, "can_delete_messages"):
        try:
            await message.delete()
        except TelegramAPIError:
            pass


@router.message(F.left_chat_member)
async def on_leave(message: Message, lang: str, db: Database) -> None:
    chat = await db.get_chat(message.chat.id)
    member = message.left_chat_member

    if chat.goodbye_on and member is not None and member.id != message.bot.id:
        template = chat.goodbye_text or t("greetings.default_goodbye", lang)
        try:
            await message.answer(render_template(template, user=member, chat=message.chat))
        except TelegramAPIError:
            pass

    if chat.cleanservice and await bot_can(message.bot, message.chat.id, "can_delete_messages"):
        try:
            await message.delete()
        except TelegramAPIError:
            pass
