from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.db import Database
from bot.i18n import t
from bot.services.gemini import GeminiClient, GeminiError
from bot.services.ratelimit import CooldownLimiter
from bot.utils.formatting import chunks, clean
from bot.utils.parsing import command_payload
from bot.utils.permissions import is_admin, is_group

router = Router(name="ai")

limiter = CooldownLimiter(calls=5, period=60)

ON_VALUES = {"on", "enable", "start", "true", "1"}
OFF_VALUES = {"off", "disable", "stop", "false", "0"}


async def _toggle(message: Message, lang: str, db: Database, settings: Settings, state: bool) -> None:
    if is_group(message.chat.type) and message.from_user is not None:
        if not await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
            await message.reply(t("common.no_permission", lang))
            return
    await db.set_chat_field(message.chat.id, "ai_enabled", state)
    await message.reply(t("ai.on", lang) if state else t("ai.off", lang))


async def ask_ai(message: Message, prompt: str, lang: str, db: Database, gemini: GeminiClient) -> None:
    if not await db.ai_globally_enabled():
        await message.reply(t("ai.global_off", lang))
        return
    chat = await db.get_chat(message.chat.id)
    if not chat.ai_enabled:
        await message.reply(t("ai.disabled_here", lang))
        return
    if not gemini.configured:
        await message.reply(t("ai.not_configured", lang))
        return
    if not prompt:
        await message.reply(t("ai.empty_prompt", lang))
        return
    if message.from_user is not None:
        wait = limiter.check(message.from_user.id)
        if wait:
            await message.reply(t("ai.rate_limited", lang, seconds=wait))
            return

    history: list[dict[str, str]] = []
    reply = message.reply_to_message
    if reply is not None and reply.text:
        role = "model" if reply.from_user is not None and reply.from_user.id == message.bot.id else "user"
        history.append({"role": role, "text": reply.text[:2000]})

    try:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    except TelegramAPIError:
        pass

    try:
        answer = await gemini.ask(prompt[:4000], lang, history)
    except GeminiError:
        await message.reply(t("ai.error", lang))
        return

    for part in chunks(clean(answer)):
        await message.reply(part)


@router.message(Command("ai", "gemini", "ask"))
async def cmd_ai(
    message: Message, lang: str, db: Database, settings: Settings, gemini: GeminiClient
) -> None:
    payload = command_payload(message.text or message.caption)
    lowered = payload.lower().strip()

    if lowered in ON_VALUES:
        await _toggle(message, lang, db, settings, True)
        return
    if lowered in OFF_VALUES:
        await _toggle(message, lang, db, settings, False)
        return

    if not payload and message.reply_to_message is not None:
        payload = message.reply_to_message.text or message.reply_to_message.caption or ""

    await ask_ai(message, payload.strip(), lang, db, gemini)


async def maybe_converse(message: Message, lang: str, db: Database, gemini: GeminiClient) -> bool:
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return False

    reply = message.reply_to_message
    replied_to_bot = reply is not None and reply.from_user is not None and reply.from_user.id == message.bot.id
    if is_group(message.chat.type) and not replied_to_bot:
        return False

    if not gemini.configured or not await db.ai_globally_enabled():
        return False
    chat = await db.get_chat(message.chat.id)
    if not chat.ai_enabled:
        return False

    await ask_ai(message, text, lang, db, gemini)
    return True
