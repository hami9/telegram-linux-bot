from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from bot.db import Database
from bot.handlers.ai import maybe_converse
from bot.handlers.antiflood import enforce_antiflood
from bot.handlers.locks import enforce_locks
from bot.handlers.notes import deliver_note
from bot.handlers.wordfilters import match_filter
from bot.services.gemini import GeminiClient
from bot.utils.permissions import is_group

router = Router(name="watchers")


@router.message(F.text | F.caption | F.sticker | F.photo | F.video | F.animation | F.document | F.voice)
async def watch(message: Message, lang: str, db: Database, gemini: GeminiClient) -> None:
    if is_group(message.chat.type):
        if await enforce_locks(message, db):
            return
        if await enforce_antiflood(message, db, lang):
            return
        if await match_filter(message, db):
            return

    text = (message.text or "").strip()
    if text.startswith("#") and len(text) > 1:
        name = text[1:].split()[0]
        if await db.get_note(message.chat.id, name) is not None:
            await deliver_note(message, db, lang, name)
            return

    await maybe_converse(message, lang, db, gemini)
