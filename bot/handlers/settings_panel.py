from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.constants import FLOOD_LIMITS, LOCK_TYPES, PUNISH_MODES, WARN_LIMITS
from bot.db import ChatConfig, Database
from bot.i18n import LANGUAGES, language_name, t
from bot.keyboards import (
    antiflood_keyboard,
    greetings_keyboard,
    language_keyboard,
    locks_keyboard,
    settings_keyboard,
    warns_keyboard,
)
from bot.utils.formatting import chat_title
from bot.utils.permissions import is_admin, is_group

router = Router(name="settings")


def _state(value: bool, lang: str) -> str:
    return t("common.on", lang) if value else t("common.off", lang)


async def _panel_text(message: Message, lang: str, settings: Settings, chat: ChatConfig, db: Database) -> str:
    footer = t("settings.footer", lang, creator=settings.creator)
    if not is_group(message.chat.type):
        body = t(
            "settings.title_private",
            lang,
            language=language_name(lang),
            ai=_state(chat.ai_enabled, lang),
        )
        return f"{body}\n\n{footer}"

    locks = await db.get_locks(message.chat.id)
    flood = t("common.off", lang) if chat.flood_limit <= 0 else str(chat.flood_limit)
    greetings = _state(chat.welcome_on or chat.goodbye_on, lang)
    body = t(
        "settings.title",
        lang,
        chat=chat_title(message.chat),
        language=language_name(lang),
        ai=_state(chat.ai_enabled, lang),
        warn_limit=chat.warn_limit,
        warn_mode=chat.warn_mode,
        flood=flood,
        greetings=greetings,
        locks=len(locks),
    )
    return f"{body}\n\n{footer}"


async def _render_main(message: Message, lang: str, settings: Settings, db: Database) -> tuple[str, object]:
    chat = await db.get_chat(message.chat.id)
    text = await _panel_text(message, lang, settings, chat, db)
    return text, settings_keyboard(lang, chat, is_group(message.chat.type))


async def _guard(callback: CallbackQuery, db: Database, settings: Settings, lang: str) -> bool:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return False
    if not is_group(message.chat.type):
        return True
    if callback.from_user is None:
        return False
    allowed = await is_admin(callback.bot, db, message.chat.id, callback.from_user.id, settings.owner_id)
    if not allowed:
        await callback.answer(t("common.admin_only_button", lang), show_alert=True)
    return allowed


async def _edit(callback: CallbackQuery, text: str, markup: object) -> None:
    if not isinstance(callback.message, Message):
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


@router.message(Command("settings", "setting", "panel"))
async def cmd_settings(message: Message, lang: str, settings: Settings, db: Database) -> None:
    if is_group(message.chat.type) and message.from_user is not None:
        if not await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
            await message.reply(t("common.no_permission", lang))
            return
    text, markup = await _render_main(message, lang, settings, db)
    await message.answer(text, reply_markup=markup)


@router.message(Command("lang", "language", "setlang"))
async def cmd_lang(message: Message, lang: str, settings: Settings, db: Database) -> None:
    if is_group(message.chat.type) and message.from_user is not None:
        if not await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
            await message.reply(t("common.no_permission", lang))
            return
    await message.answer(
        t("settings.language_title", lang, language=language_name(lang)),
        reply_markup=language_keyboard(lang),
    )


@router.callback_query(F.data == "s:main")
async def cb_main(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    message = callback.message
    if isinstance(message, Message):
        text, markup = await _render_main(message, lang, settings, db)
        await _edit(callback, text, markup)
    await callback.answer()


@router.callback_query(F.data == "s:ai")
async def cb_toggle_ai(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    message = callback.message
    if not isinstance(message, Message):
        return
    enabled = await db.toggle_chat_flag(message.chat.id, "ai_enabled")
    text, markup = await _render_main(message, lang, settings, db)
    await _edit(callback, text, markup)
    await callback.answer(t("ai.on", lang) if enabled else t("ai.off", lang))


@router.callback_query(F.data == "s:lang")
async def cb_language_menu(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    await _edit(
        callback,
        t("settings.language_title", lang, language=language_name(lang)),
        language_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("s:lang:"))
async def cb_language_set(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    code = (callback.data or "").split(":")[-1]
    if code not in LANGUAGES:
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    message = callback.message
    if not isinstance(message, Message):
        return
    if is_group(message.chat.type):
        await db.set_chat_field(message.chat.id, "lang", code)
    elif callback.from_user is not None:
        await db.set_user_lang(callback.from_user.id, code)
    text, markup = await _render_main(message, code, settings, db)
    await _edit(callback, text, markup)
    await callback.answer(t("settings.language_set", code, language=language_name(code)))


@router.callback_query(F.data == "s:locks")
async def cb_locks(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    message = callback.message
    if not isinstance(message, Message):
        return
    locked = await db.get_locks(message.chat.id)
    await _edit(callback, t("settings.locks_title", lang), locks_keyboard(lang, locked))
    await callback.answer()


@router.callback_query(F.data.startswith("s:lock:"))
async def cb_lock_toggle(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    lock_type = (callback.data or "").split(":")[-1]
    message = callback.message
    if lock_type not in LOCK_TYPES or not isinstance(message, Message):
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    enabled = await db.toggle_lock(message.chat.id, lock_type)
    locked = await db.get_locks(message.chat.id)
    await _edit(callback, t("settings.locks_title", lang), locks_keyboard(lang, locked))
    await callback.answer(
        t("locks.locked", lang, type=lock_type) if enabled else t("locks.unlocked", lang, type=lock_type)
    )


@router.callback_query(F.data == "s:greet")
async def cb_greetings(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    message = callback.message
    if not isinstance(message, Message):
        return
    chat = await db.get_chat(message.chat.id)
    await _edit(
        callback,
        t(
            "settings.greetings_title",
            lang,
            welcome=_state(chat.welcome_on, lang),
            goodbye=_state(chat.goodbye_on, lang),
            cleanservice=_state(chat.cleanservice, lang),
        ),
        greetings_keyboard(lang, chat),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("s:greet:"))
async def cb_greetings_toggle(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    action = (callback.data or "").split(":")[-1]
    field = {"welcome": "welcome_on", "goodbye": "goodbye_on", "clean": "cleanservice"}.get(action)
    message = callback.message
    if field is None or not isinstance(message, Message):
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    await db.toggle_chat_flag(message.chat.id, field)
    chat = await db.get_chat(message.chat.id)
    await _edit(
        callback,
        t(
            "settings.greetings_title",
            lang,
            welcome=_state(chat.welcome_on, lang),
            goodbye=_state(chat.goodbye_on, lang),
            cleanservice=_state(chat.cleanservice, lang),
        ),
        greetings_keyboard(lang, chat),
    )
    await callback.answer(t("settings.saved", lang))


@router.callback_query(F.data == "s:flood")
async def cb_flood(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    message = callback.message
    if not isinstance(message, Message):
        return
    chat = await db.get_chat(message.chat.id)
    limit = t("common.off", lang) if chat.flood_limit <= 0 else str(chat.flood_limit)
    await _edit(
        callback,
        t("settings.antiflood_title", lang, limit=limit, mode=chat.flood_mode),
        antiflood_keyboard(lang, chat),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("s:flood:"))
async def cb_flood_set(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    parts = (callback.data or "").split(":")
    message = callback.message
    if len(parts) != 4 or not isinstance(message, Message):
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    kind, value = parts[2], parts[3]
    if kind == "limit" and value.isdigit() and int(value) in FLOOD_LIMITS:
        await db.set_chat_field(message.chat.id, "flood_limit", int(value))
    elif kind == "mode" and value in PUNISH_MODES:
        await db.set_chat_field(message.chat.id, "flood_mode", value)
    else:
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    chat = await db.get_chat(message.chat.id)
    limit = t("common.off", lang) if chat.flood_limit <= 0 else str(chat.flood_limit)
    await _edit(
        callback,
        t("settings.antiflood_title", lang, limit=limit, mode=chat.flood_mode),
        antiflood_keyboard(lang, chat),
    )
    await callback.answer(t("settings.saved", lang))


@router.callback_query(F.data == "s:warns")
async def cb_warns(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    message = callback.message
    if not isinstance(message, Message):
        return
    chat = await db.get_chat(message.chat.id)
    await _edit(
        callback,
        t("settings.warns_title", lang, limit=chat.warn_limit, mode=chat.warn_mode),
        warns_keyboard(lang, chat),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("s:warns:"))
async def cb_warns_set(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    parts = (callback.data or "").split(":")
    message = callback.message
    if len(parts) != 4 or not isinstance(message, Message):
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    kind, value = parts[2], parts[3]
    if kind == "limit" and value.isdigit() and int(value) in WARN_LIMITS:
        await db.set_chat_field(message.chat.id, "warn_limit", int(value))
    elif kind == "mode" and value in PUNISH_MODES:
        await db.set_chat_field(message.chat.id, "warn_mode", value)
    else:
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    chat = await db.get_chat(message.chat.id)
    await _edit(
        callback,
        t("settings.warns_title", lang, limit=chat.warn_limit, mode=chat.warn_mode),
        warns_keyboard(lang, chat),
    )
    await callback.answer(t("settings.saved", lang))


@router.callback_query(F.data == "s:close")
async def cb_close(callback: CallbackQuery, lang: str, settings: Settings, db: Database) -> None:
    if not await _guard(callback, db, settings, lang):
        return
    if isinstance(callback.message, Message):
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    await callback.answer()
