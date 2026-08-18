from __future__ import annotations

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message, ReplyParameters

from bot.config import Settings
from bot.db import Database
from bot.handlers.terminal import clear_terminal
from bot.i18n import t
from bot.utils.formatting import clean
from bot.utils.parsing import split_command_args
from bot.utils.permissions import is_admin, is_group

router = Router(name="notes")

MEDIA_KINDS = ("photo", "video", "animation", "document", "sticker", "voice", "audio")


def extract_media(message: Message) -> tuple[str, str]:
    for kind in MEDIA_KINDS:
        value = getattr(message, kind, None)
        if value is None:
            continue
        if kind == "photo":
            return kind, value[-1].file_id
        return kind, value.file_id
    return "text", ""


async def _require_admin(message: Message, db: Database, settings: Settings, lang: str) -> bool:
    if not is_group(message.chat.type):
        return True
    if message.from_user is None:
        return False
    if await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
        return True
    await message.reply(t("common.no_permission", lang))
    return False


async def send_stored(bot: Bot, chat_id: int, reply_to: int | None, item: dict[str, str]) -> None:
    kind = item.get("kind", "text")
    content = item.get("content", "")
    file_id = item.get("file_id", "")
    reply = ReplyParameters(message_id=reply_to, allow_sending_without_reply=True) if reply_to else None
    try:
        if kind == "text" or not file_id:
            if content:
                await bot.send_message(chat_id, content, reply_parameters=reply)
            return
        sender = {
            "photo": bot.send_photo,
            "video": bot.send_video,
            "animation": bot.send_animation,
            "document": bot.send_document,
            "sticker": bot.send_sticker,
            "voice": bot.send_voice,
            "audio": bot.send_audio,
        }.get(kind)
        if sender is None:
            return
        if kind == "sticker":
            await sender(chat_id, file_id, reply_parameters=reply)
        else:
            await sender(chat_id, file_id, caption=content or None, reply_parameters=reply)
    except TelegramAPIError:
        return


@router.message(Command("save", "addnote"))
async def cmd_save(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or message.caption)
    if not args:
        await message.reply(t("notes.need_name", lang))
        return
    name = args[0].lstrip("#").lower()
    inline_content = " ".join(args[1:]).strip()

    source = message.reply_to_message
    if source is not None:
        kind, file_id = extract_media(source)
        content = source.html_text if (source.text or source.caption) else ""
    else:
        kind, file_id = "text", ""
        content = clean(inline_content)

    if not content and not file_id:
        await message.reply(t("notes.need_content", lang))
        return

    await db.save_note(message.chat.id, name, content, kind, file_id)
    await message.reply(t("notes.saved", lang, name=clean(name)))


@router.message(Command("get"))
async def cmd_get(message: Message, lang: str, db: Database) -> None:
    args = split_command_args(message.text or "")
    if not args:
        await message.reply(t("notes.need_name", lang))
        return
    await deliver_note(message, db, lang, args[0].lstrip("#"))


@router.message(Command("clear", "rmnote"))
async def cmd_clear(message: Message, lang: str, db: Database, settings: Settings) -> None:
    args = split_command_args(message.text or "")
    if args and args[0].lower() in {"--terminal", "-t", "terminal"}:
        await clear_terminal(message, lang, db, settings)
        return
    if not await _require_admin(message, db, settings, lang):
        return
    if not args:
        await message.reply(t("notes.need_name", lang))
        return
    name = args[0].lstrip("#").lower()
    if await db.delete_note(message.chat.id, name):
        await message.reply(t("notes.deleted", lang, name=clean(name)))
    else:
        await message.reply(t("notes.not_found", lang, name=clean(name)))


@router.message(Command("notes", "saved"))
async def cmd_notes(message: Message, lang: str, db: Database) -> None:
    names = await db.list_notes(message.chat.id)
    if not names:
        await message.reply(t("notes.empty", lang))
        return
    listed = "\n".join(f"• <code>#{clean(name)}</code>" for name in names)
    await message.reply(f"{t('notes.list_title', lang)}\n{listed}")


async def deliver_note(message: Message, db: Database, lang: str, name: str) -> bool:
    item = await db.get_note(message.chat.id, name)
    if item is None:
        await message.reply(t("notes.not_found", lang, name=clean(name)))
        return False
    await send_stored(message.bot, message.chat.id, message.message_id, item)
    return True
