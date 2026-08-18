from __future__ import annotations

import asyncio

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.db import Database
from bot.filters import IsOwner
from bot.i18n import t
from bot.utils.formatting import clean
from bot.utils.parsing import command_payload, split_command_args
from bot.utils.targeting import resolve_target

router = Router(name="owner")
router.message.filter(IsOwner())


@router.message(Command("sudo", "sudoers"))
async def cmd_sudo(message: Message, lang: str, db: Database) -> None:
    args = split_command_args(message.text or "")
    action = args[0].lower() if args else "list"

    if action == "list":
        users = await db.list_sudo()
        if not users:
            await message.reply(t("owner.sudo_empty", lang))
            return
        lines = [t("owner.sudo_list", lang)]
        for user_id in users:
            lines.append(f"• <code>{user_id}</code> — {clean(await db.get_user_label(user_id))}")
        await message.reply("\n".join(lines))
        return

    target = await resolve_target(message, db, args[1:])
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return

    if action in {"add", "promote"}:
        await db.add_sudo(target.user_id)
        await message.reply(t("owner.sudo_added", lang, user=target.html))
    elif action in {"del", "remove", "rm"}:
        await db.remove_sudo(target.user_id)
        await message.reply(t("owner.sudo_removed", lang, user=target.html))
    else:
        await message.reply(t("common.error", lang))


@router.message(Command("stats", "gstats"))
async def cmd_stats(message: Message, lang: str, db: Database, settings: Settings) -> None:
    data = await db.stats()
    await message.reply(t("owner.stats", lang, version=settings.version, **data))


@router.message(Command("aiglobal"))
async def cmd_ai_global(message: Message, lang: str, db: Database) -> None:
    args = split_command_args(message.text or "")
    value = args[0].lower() if args else ""
    if value in {"on", "1", "enable"}:
        enabled = True
    elif value in {"off", "0", "disable"}:
        enabled = False
    else:
        enabled = not await db.ai_globally_enabled()
    await db.set_ai_global(enabled)
    state = t("common.enabled", lang) if enabled else t("common.disabled", lang)
    await message.reply(t("owner.ai_global", lang, state=state))


@router.message(Command("broadcast", "announce"))
async def cmd_broadcast(message: Message, lang: str, db: Database) -> None:
    text = command_payload(message.text or "")
    if not text and message.reply_to_message is not None and message.reply_to_message.text:
        text = message.reply_to_message.html_text
    if not text:
        await message.reply(t("owner.broadcast_need_text", lang))
        return

    ok = 0
    failed = 0
    for chat_id in await db.all_chat_ids():
        try:
            await message.bot.send_message(chat_id, text)
            ok += 1
        except TelegramAPIError:
            failed += 1
        await asyncio.sleep(0.05)
    await message.reply(t("owner.broadcast_done", lang, ok=ok, failed=failed))
