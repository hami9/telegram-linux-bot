from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.i18n import t
from bot.keyboards import about_keyboard

router = Router(name="about")


@router.message(Command("about", "credits"))
async def cmd_about(message: Message, lang: str, settings: Settings) -> None:
    await message.answer(
        t("about.card", lang, version=settings.version, creator=settings.creator),
        reply_markup=about_keyboard(lang, settings),
    )
