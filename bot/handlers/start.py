from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.constants import HELP_CATEGORIES
from bot.i18n import t
from bot.keyboards import help_back_keyboard, help_keyboard, start_keyboard
from bot.utils.permissions import is_group

router = Router(name="start")


def _footer(lang: str, settings: Settings) -> str:
    return t("common.creator", lang, creator=settings.creator)


@router.message(CommandStart())
async def cmd_start(message: Message, lang: str, settings: Settings) -> None:
    private = not is_group(message.chat.type)
    body = t("start.private", lang) if private else t("start.group", lang)
    me = await message.bot.me()
    await message.answer(
        f"{body}\n\n{_footer(lang, settings)}",
        reply_markup=start_keyboard(lang, settings, me.username or "", private),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str, settings: Settings) -> None:
    await message.answer(
        f"{t('help.title', lang)}\n\n{_footer(lang, settings)}",
        reply_markup=help_keyboard(lang),
    )


@router.callback_query(F.data == "help:menu")
async def cb_help_menu(callback: CallbackQuery, lang: str, settings: Settings) -> None:
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(
                f"{t('help.title', lang)}\n\n{_footer(lang, settings)}",
                reply_markup=help_keyboard(lang),
            )
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("help:cat:"))
async def cb_help_category(callback: CallbackQuery, lang: str, settings: Settings) -> None:
    category = (callback.data or "").split(":")[-1]
    if category not in HELP_CATEGORIES:
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(
                f"{t(f'help.body_{category}', lang)}\n\n{_footer(lang, settings)}",
                reply_markup=help_back_keyboard(lang),
            )
        except TelegramBadRequest:
            pass
    await callback.answer()
