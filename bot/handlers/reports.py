from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from bot.db import Database
from bot.filters import IsGroup
from bot.i18n import t
from bot.utils.formatting import chat_title, clean, mention
from bot.utils.parsing import command_payload
from bot.utils.permissions import is_chat_admin

router = Router(name="reports")
router.message.filter(IsGroup())


async def deliver_report(message: Message, lang: str) -> None:
    if message.reply_to_message is None or message.from_user is None:
        await message.reply(t("reports.need_reply", lang))
        return
    culprit = message.reply_to_message.from_user
    if culprit is None:
        await message.reply(t("reports.need_reply", lang))
        return
    if await is_chat_admin(message.bot, message.chat.id, culprit.id):
        await message.reply(t("reports.not_admin_target", lang))
        return

    reason = clean(command_payload(message.text or "")) or t("common.no_reason", lang)
    header = t(
        "reports.header",
        lang,
        user=mention(message.from_user),
        chat=chat_title(message.chat),
        reason_label=t("common.reason", lang),
        reason=reason,
    )
    link = message.reply_to_message.get_url() or ""
    body = f"{header}\n{link}".strip()

    delivered = 0
    try:
        admins = await message.bot.get_chat_administrators(message.chat.id)
    except TelegramAPIError:
        admins = []
    for admin in admins:
        if admin.user.is_bot:
            continue
        try:
            await message.bot.send_message(admin.user.id, body)
            delivered += 1
        except TelegramAPIError:
            continue
    await message.reply(t("reports.sent", lang, count=delivered))


@router.message(Command("report"))
async def cmd_report(message: Message, lang: str, db: Database) -> None:
    await deliver_report(message, lang)


@router.message(F.reply_to_message, F.text.lower().contains("@admin"))
async def trigger_report(message: Message, lang: str, db: Database) -> None:
    await deliver_report(message, lang)
