from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import Settings
from bot.constants import (
    BOT_RIGHTS,
    FLOOD_LIMITS,
    HELP_CATEGORIES,
    LOCK_TYPES,
    MEMBER_PERMISSIONS,
    PUNISH_MODES,
    WARN_LIMITS,
)
from bot.db import ChatConfig
from bot.i18n import LANGUAGES, t


def _state(value: bool, lang: str) -> str:
    return t("common.on", lang) if value else t("common.off", lang)


def start_keyboard(lang: str, settings: Settings, bot_username: str, private: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if private and bot_username:
        builder.row(
            InlineKeyboardButton(
                text=t("start.btn_add", lang),
                url=f"https://t.me/{bot_username}?startgroup=true",
            )
        )
    builder.row(
        InlineKeyboardButton(text=t("start.btn_help", lang), callback_data="help:menu"),
        InlineKeyboardButton(text=t("start.btn_settings", lang), callback_data="s:main"),
    )
    builder.row(
        InlineKeyboardButton(text=t("start.btn_source", lang), url=settings.source_url),
        InlineKeyboardButton(text=t("start.btn_creator", lang), url=settings.creator_url),
    )
    return builder.as_markup()


def help_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in HELP_CATEGORIES:
        builder.button(text=t(f"help.cat_{category}", lang), callback_data=f"help:cat:{category}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t("common.close", lang), callback_data="s:close"))
    return builder.as_markup()


def help_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("common.back", lang), callback_data="help:menu"),
        InlineKeyboardButton(text=t("common.close", lang), callback_data="s:close"),
    )
    return builder.as_markup()


def settings_keyboard(lang: str, chat: ChatConfig, group: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("settings.btn_ai", lang, state=_state(chat.ai_enabled, lang)),
            callback_data="s:ai",
        )
    )
    builder.row(InlineKeyboardButton(text=t("settings.btn_language", lang), callback_data="s:lang"))
    if group:
        builder.row(
            InlineKeyboardButton(text=t("settings.btn_locks", lang), callback_data="s:locks"),
            InlineKeyboardButton(text=t("settings.btn_greetings", lang), callback_data="s:greet"),
        )
        builder.row(
            InlineKeyboardButton(text=t("settings.btn_antiflood", lang), callback_data="s:flood"),
            InlineKeyboardButton(text=t("settings.btn_warns", lang), callback_data="s:warns"),
        )
    builder.row(InlineKeyboardButton(text=t("common.close", lang), callback_data="s:close"))
    return builder.as_markup()


def language_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in LANGUAGES.items():
        marker = "✅ " if code == lang else ""
        builder.button(text=f"{marker}{title}", callback_data=f"s:lang:{code}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t("common.back", lang), callback_data="s:main"))
    return builder.as_markup()


def locks_keyboard(lang: str, locked: set[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for lock_type in LOCK_TYPES:
        marker = "🔒" if lock_type in locked else "🔓"
        builder.button(text=f"{marker} {lock_type}", callback_data=f"s:lock:{lock_type}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t("common.back", lang), callback_data="s:main"))
    return builder.as_markup()


def greetings_keyboard(lang: str, chat: ChatConfig) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("settings.btn_welcome", lang, state=_state(chat.welcome_on, lang)),
            callback_data="s:greet:welcome",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("settings.btn_goodbye", lang, state=_state(chat.goodbye_on, lang)),
            callback_data="s:greet:goodbye",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("settings.btn_cleanservice", lang, state=_state(chat.cleanservice, lang)),
            callback_data="s:greet:clean",
        )
    )
    builder.row(InlineKeyboardButton(text=t("common.back", lang), callback_data="s:main"))
    return builder.as_markup()


def antiflood_keyboard(lang: str, chat: ChatConfig) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for limit in FLOOD_LIMITS:
        label = t("common.off", lang) if limit == 0 else str(limit)
        marker = "✅ " if limit == chat.flood_limit else ""
        builder.button(text=f"{marker}{label}", callback_data=f"s:flood:limit:{limit}")
    builder.adjust(3)
    row = []
    for mode in PUNISH_MODES:
        marker = "✅ " if mode == chat.flood_mode else ""
        row.append(InlineKeyboardButton(text=f"{marker}{mode}", callback_data=f"s:flood:mode:{mode}"))
    builder.row(*row)
    builder.row(InlineKeyboardButton(text=t("common.back", lang), callback_data="s:main"))
    return builder.as_markup()


def warns_keyboard(lang: str, chat: ChatConfig) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for limit in WARN_LIMITS:
        marker = "✅ " if limit == chat.warn_limit else ""
        builder.button(text=f"{marker}{limit}", callback_data=f"s:warns:limit:{limit}")
    builder.adjust(5)
    row = []
    for mode in PUNISH_MODES:
        marker = "✅ " if mode == chat.warn_mode else ""
        row.append(InlineKeyboardButton(text=f"{marker}{mode}", callback_data=f"s:warns:mode:{mode}"))
    builder.row(*row)
    builder.row(InlineKeyboardButton(text=t("common.back", lang), callback_data="s:main"))
    return builder.as_markup()


def rights_keyboard(lang: str, user_id: int, rights: dict[str, bool]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for right in BOT_RIGHTS:
        marker = "✅" if rights.get(right, False) else "❌"
        builder.button(
            text=f"{marker} {t(f'roles.right_{right}', lang)}",
            callback_data=f"perm:{user_id}:{right}",
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t("common.close", lang), callback_data="s:close"))
    return builder.as_markup()


def member_perms_keyboard(lang: str, user_id: int, allowed: dict[str, bool]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name in MEMBER_PERMISSIONS:
        marker = "✅" if allowed.get(name, True) else "🚫"
        builder.button(
            text=f"{marker} {t(f'roles.perm_{name}', lang)}",
            callback_data=f"mperm:{user_id}:{name}",
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t("common.close", lang), callback_data="s:close"))
    return builder.as_markup()


def about_keyboard(lang: str, settings: Settings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("about.btn_creator", lang, creator=settings.creator), url=settings.creator_url
        )
    )
    builder.row(InlineKeyboardButton(text=t("about.btn_source", lang), url=settings.source_url))
    return builder.as_markup()
