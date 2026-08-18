from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.constants import PUNISH_MODES
from bot.db import Database
from bot.filters import IsGroup
from bot.handlers.admin import punish
from bot.i18n import t
from bot.utils.formatting import clean, mention
from bot.utils.parsing import split_command_args
from bot.utils.permissions import bot_can, is_admin, is_chat_admin
from bot.utils.targeting import resolve_target

router = Router(name="warns")
router.message.filter(IsGroup())


async def _require_admin(message: Message, db: Database, settings: Settings, lang: str) -> bool:
    if message.from_user is None:
        return False
    if await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id):
        return True
    await message.reply(t("common.no_permission", lang))
    return False


async def apply_warn(
    message: Message, db: Database, lang: str, user_id: int, user_html: str, reason: str
) -> None:
    chat = await db.get_chat(message.chat.id)
    reasons = await db.add_warn(message.chat.id, user_id, reason)
    if len(reasons) < chat.warn_limit:
        await message.reply(
            t(
                "warns.warned",
                lang,
                user=user_html,
                count=len(reasons),
                limit=chat.warn_limit,
                reason_label=t("common.reason", lang),
                reason=reason,
            )
        )
        return

    if not await bot_can(message.bot, message.chat.id, "can_restrict_members"):
        await message.reply(t("common.need_right", lang, right="can_restrict_members"))
        return
    if not await punish(message.bot, message.chat.id, user_id, chat.warn_mode):
        await message.reply(t("common.error", lang))
        return
    await db.reset_warns(message.chat.id, user_id)
    await message.reply(t("warns.limit_hit", lang, user=user_html, action=chat.warn_mode))


@router.message(Command("warn", "dwarn"))
async def cmd_warn(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or message.caption)
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    if target.user_id == message.bot.id:
        await message.reply(t("common.target_is_self", lang))
        return
    if await is_chat_admin(message.bot, message.chat.id, target.user_id):
        await message.reply(t("common.target_is_admin", lang))
        return

    invoked = ((message.text or message.caption or "").split() or [""])[0]
    if invoked.lstrip("/").split("@")[0].lower() == "dwarn" and message.reply_to_message is not None:
        try:
            await message.reply_to_message.delete()
        except TelegramBadRequest:
            pass

    raw_reason = " ".join(args[target.consumed_args :]).strip()
    reason = clean(raw_reason) if raw_reason else t("common.no_reason", lang)
    await apply_warn(message, db, lang, target.user_id, target.html, reason)


@router.message(Command("unwarn", "rmwarn"))
async def cmd_unwarn(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    chat = await db.get_chat(message.chat.id)
    reasons = await db.remove_warn(message.chat.id, target.user_id)
    await message.reply(
        t("warns.removed", lang, user=target.html, count=len(reasons), limit=chat.warn_limit)
    )


@router.message(Command("resetwarn", "resetwarns"))
async def cmd_resetwarn(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    await db.reset_warns(message.chat.id, target.user_id)
    await message.reply(t("warns.reset", lang, user=target.html))


@router.message(Command("warns", "warnings"))
async def cmd_warns(message: Message, lang: str, db: Database) -> None:
    args = split_command_args(message.text or "")
    target = await resolve_target(message, db, args)
    if target is None and message.from_user is not None:
        target_html = mention(message.from_user)
        user_id = message.from_user.id
    elif target is not None:
        target_html = target.html
        user_id = target.user_id
    else:
        await message.reply(t("common.reply_or_username", lang))
        return

    chat = await db.get_chat(message.chat.id)
    reasons = await db.get_warns(message.chat.id, user_id)
    if not reasons:
        await message.reply(t("warns.none", lang, user=target_html))
        return
    listed = "\n".join(f"{index}. {reason}" for index, reason in enumerate(reasons, start=1))
    await message.reply(
        t("warns.list", lang, user=target_html, count=len(reasons), limit=chat.warn_limit, reasons=listed)
    )


@router.message(Command("warnlimit", "setwarnlimit"))
async def cmd_warnlimit(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    if not args or not args[0].isdigit() or not 1 <= int(args[0]) <= 20:
        await message.reply(t("warns.limit_invalid", lang))
        return
    await db.set_chat_field(message.chat.id, "warn_limit", int(args[0]))
    await message.reply(t("warns.limit_set", lang, limit=int(args[0])))


@router.message(Command("warnmode", "setwarnmode"))
async def cmd_warnmode(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await _require_admin(message, db, settings, lang):
        return
    args = split_command_args(message.text or "")
    if not args or args[0].lower() not in PUNISH_MODES:
        await message.reply(t("warns.mode_invalid", lang))
        return
    await db.set_chat_field(message.chat.id, "warn_mode", args[0].lower())
    await message.reply(t("warns.mode_set", lang, mode=args[0].lower()))
