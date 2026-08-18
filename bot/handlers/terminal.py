from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from bot.config import Settings
from bot.db import Database
from bot.handlers.admin import punish, purge_range
from bot.utils.access import require_right
from bot.i18n import t
from bot.utils.formatting import clean, full_name
from bot.utils.permissions import bot_can, is_chat_admin, privilege_level
from bot.utils.targeting import resolve_target

router = Router(name="terminal")

LEVEL_KEYS = {"root": "terminal.level_root", "sudoers": "terminal.level_sudo", "user": "terminal.level_user"}


@router.message(F.text.lower().strip() == "whoami")
async def cmd_whoami(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if message.from_user is None:
        return
    level = await privilege_level(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id)
    await message.reply(
        t(
            "terminal.whoami",
            lang,
            name=clean(full_name(message.from_user)),
            id=message.from_user.id,
            chat_id=message.chat.id,
            level=t(LEVEL_KEYS.get(level, "terminal.level_user"), lang),
        )
    )


@router.message(F.text.lower().startswith("sudo userdel"))
async def cmd_userdel(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if message.from_user is None:
        return
    if not await require_right(message, db, settings, lang, "ban"):
        return
    if not await bot_can(message.bot, message.chat.id, "can_restrict_members"):
        await message.reply(t("common.need_right", lang, right="can_restrict_members"))
        return

    tokens = [token for token in (message.text or "").split()[2:] if not token.startswith("-")]
    force = "-f" in (message.text or "").split()
    target = await resolve_target(message, db, tokens)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    if target.user_id == message.bot.id or target.user_id == message.from_user.id:
        await message.reply(t("common.target_is_self", lang))
        return
    if await is_chat_admin(message.bot, message.chat.id, target.user_id):
        await message.reply(t("common.target_is_admin", lang))
        return

    mode = "ban" if force else "kick"
    if not await punish(message.bot, message.chat.id, target.user_id, mode):
        await message.reply(t("common.error", lang))
        return
    key = "admin.banned" if force else "admin.kicked"
    await message.reply(
        t(
            key,
            lang,
            user=target.html,
            reason_label=t("common.reason", lang),
            reason=f"<code>sudo userdel {'-f ' if force else ''}</code>",
        )
    )


@router.message(F.text.lower().startswith("clear --terminal") | (F.text.lower().strip() == "clear"))
async def cmd_clear_terminal(message: Message, lang: str, db: Database, settings: Settings) -> None:
    await clear_terminal(message, lang, db, settings)


async def clear_terminal(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if message.from_user is None:
        return
    if not await require_right(message, db, settings, lang, "delete"):
        return
    if not await bot_can(message.bot, message.chat.id, "can_delete_messages"):
        await message.reply(t("common.need_right", lang, right="can_delete_messages"))
        return
    if message.reply_to_message is None:
        await message.reply(t("admin.purge_reply", lang))
        return
    deleted = await purge_range(
        message.bot, message.chat.id, message.reply_to_message.message_id, message.message_id
    )
    if deleted == 0:
        await message.reply(t("admin.purge_limit", lang))
        return
    await message.answer(t("terminal.cleared", lang, count=deleted))
