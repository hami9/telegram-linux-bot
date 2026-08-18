from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.db import Database
from bot.filters import IsGroup
from bot.handlers.notes import extract_media, send_stored
from bot.utils.access import require_right
from bot.i18n import t
from bot.utils.formatting import clean
from bot.utils.parsing import split_command_args

router = Router(name="wordfilters")
router.message.filter(IsGroup())




@router.message(Command("filter", "addfilter"))
async def cmd_filter(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "notes"):
        return
    args = split_command_args(message.text or message.caption)
    if not args:
        await message.reply(t("filters.need_keyword", lang))
        return
    keyword = args[0].lower()
    inline_content = " ".join(args[1:]).strip()

    source = message.reply_to_message
    if source is not None:
        kind, file_id = extract_media(source)
        content = source.html_text if (source.text or source.caption) else ""
    else:
        kind, file_id = "text", ""
        content = clean(inline_content)

    if not content and not file_id:
        await message.reply(t("filters.need_keyword", lang))
        return

    await db.save_filter(message.chat.id, keyword, content, kind, file_id)
    await message.reply(t("filters.saved", lang, keyword=clean(keyword)))


@router.message(Command("stop", "rmfilter"))
async def cmd_stop(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "notes"):
        return
    args = split_command_args(message.text or "")
    if not args:
        await message.reply(t("filters.need_keyword", lang))
        return
    keyword = args[0].lower()
    if await db.delete_filter(message.chat.id, keyword):
        await message.reply(t("filters.removed", lang, keyword=clean(keyword)))
    else:
        await message.reply(t("filters.not_found", lang, keyword=clean(keyword)))


@router.message(Command("filters", "filterlist"))
async def cmd_filters(message: Message, lang: str, db: Database) -> None:
    items = await db.list_filters(message.chat.id)
    if not items:
        await message.reply(t("filters.empty", lang))
        return
    listed = "\n".join(f"• <code>{clean(item['keyword'])}</code>" for item in items)
    await message.reply(f"{t('filters.list_title', lang)}\n{listed}")


async def match_filter(message: Message, db: Database) -> bool:
    text = (message.text or message.caption or "").lower()
    if not text:
        return False
    items = await db.list_filters(message.chat.id)
    if not items:
        return False
    words = set(text.split())
    for item in items:
        keyword = item["keyword"]
        hit = keyword in words if " " not in keyword else keyword in text
        if hit:
            await send_stored(message.bot, message.chat.id, message.message_id, item)
            return True
    return False
