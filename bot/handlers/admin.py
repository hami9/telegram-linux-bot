from __future__ import annotations

from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from bot.config import Settings
from bot.constants import MUTED_PERMISSIONS, UNMUTED_PERMISSIONS
from bot.db import Database
from bot.filters import IsGroup
from bot.utils.access import require_right
from bot.i18n import t
from bot.utils.formatting import chat_title, clean, mention
from bot.utils.parsing import humanize_duration, parse_duration, split_command_args, until_date
from bot.utils.permissions import bot_can, get_member, is_chat_admin, privilege_level
from bot.utils.targeting import Target, resolve_target

router = Router(name="admin")
router.message.filter(IsGroup())

PURGE_BATCH = 100


async def _bot_needs(message: Message, lang: str, right: str) -> bool:
    if await bot_can(message.bot, message.chat.id, right):
        return True
    await message.reply(t("common.need_right", lang, right=right))
    return False


async def _pick_target(
    message: Message, db: Database, lang: str, args: list[str], protect_admins: bool = True
) -> Target | None:
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return None
    if target.user_id == message.bot.id:
        await message.reply(t("common.target_is_self", lang))
        return None
    if message.from_user is not None and target.user_id == message.from_user.id:
        await message.reply(t("common.target_is_you", lang))
        return None
    if protect_admins and await is_chat_admin(message.bot, message.chat.id, target.user_id):
        await message.reply(t("common.target_is_admin", lang))
        return None
    return target


def _reason(lang: str, args: list[str], skip: int) -> str:
    text = " ".join(args[skip:]).strip()
    return clean(text) if text else t("common.no_reason", lang)


async def punish(
    bot: Bot,
    chat_id: int,
    user_id: int,
    mode: str,
    seconds: int | None = None,
) -> bool:
    try:
        if mode == "ban":
            await bot.ban_chat_member(chat_id, user_id, until_date=until_date(seconds) if seconds else None)
        elif mode == "kick":
            await bot.ban_chat_member(chat_id, user_id)
            await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        else:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=ChatPermissions(**MUTED_PERMISSIONS),
                until_date=until_date(seconds) if seconds else None,
            )
        return True
    except TelegramAPIError:
        return False


@router.message(Command("ban", "sban"))
async def cmd_ban(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "ban") or not await _bot_needs(
        message, lang, "can_restrict_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await _pick_target(message, db, lang, args)
    if target is None:
        return
    if not await punish(message.bot, message.chat.id, target.user_id, "ban"):
        await message.reply(t("common.error", lang))
        return
    invoked = ((message.text or message.caption or "").split() or [""])[0]
    if invoked.lstrip("/").split("@")[0].lower() == "sban":
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        return
    await message.reply(
        t(
            "admin.banned",
            lang,
            user=target.html,
            reason_label=t("common.reason", lang),
            reason=_reason(lang, args, target.consumed_args),
        )
    )


@router.message(Command("tban", "tempban"))
async def cmd_tban(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "ban") or not await _bot_needs(
        message, lang, "can_restrict_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await _pick_target(message, db, lang, args)
    if target is None:
        return
    duration_arg = args[target.consumed_args] if len(args) > target.consumed_args else None
    seconds = parse_duration(duration_arg)
    if seconds is None:
        await message.reply(t("admin.invalid_duration", lang))
        return
    if not await punish(message.bot, message.chat.id, target.user_id, "ban", seconds):
        await message.reply(t("common.error", lang))
        return
    await message.reply(
        t(
            "admin.tbanned",
            lang,
            user=target.html,
            duration=humanize_duration(seconds),
            reason_label=t("common.reason", lang),
            reason=_reason(lang, args, target.consumed_args + 1),
        )
    )


@router.message(Command("unban"))
async def cmd_unban(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "ban") or not await _bot_needs(
        message, lang, "can_restrict_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    try:
        await message.bot.unban_chat_member(message.chat.id, target.user_id, only_if_banned=True)
    except TelegramAPIError:
        await message.reply(t("common.error", lang))
        return
    await message.reply(t("admin.unbanned", lang, user=target.html))


@router.message(Command("kick", "punch"))
async def cmd_kick(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "ban") or not await _bot_needs(
        message, lang, "can_restrict_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await _pick_target(message, db, lang, args)
    if target is None:
        return
    if not await punish(message.bot, message.chat.id, target.user_id, "kick"):
        await message.reply(t("common.error", lang))
        return
    await message.reply(
        t(
            "admin.kicked",
            lang,
            user=target.html,
            reason_label=t("common.reason", lang),
            reason=_reason(lang, args, target.consumed_args),
        )
    )


@router.message(Command("kickme"))
async def cmd_kickme(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if message.from_user is None:
        return
    if await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.reply(t("common.target_is_admin", lang))
        return
    if not await _bot_needs(message, lang, "can_restrict_members"):
        return
    if not await punish(message.bot, message.chat.id, message.from_user.id, "kick"):
        await message.reply(t("common.error", lang))
        return
    await message.reply(t("admin.kickme", lang))


@router.message(Command("mute"))
async def cmd_mute(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "mute") or not await _bot_needs(
        message, lang, "can_restrict_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await _pick_target(message, db, lang, args)
    if target is None:
        return
    if not await punish(message.bot, message.chat.id, target.user_id, "mute"):
        await message.reply(t("common.error", lang))
        return
    await message.reply(
        t(
            "admin.muted",
            lang,
            user=target.html,
            reason_label=t("common.reason", lang),
            reason=_reason(lang, args, target.consumed_args),
        )
    )


@router.message(Command("tmute", "tempmute"))
async def cmd_tmute(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "mute") or not await _bot_needs(
        message, lang, "can_restrict_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await _pick_target(message, db, lang, args)
    if target is None:
        return
    duration_arg = args[target.consumed_args] if len(args) > target.consumed_args else None
    seconds = parse_duration(duration_arg)
    if seconds is None:
        await message.reply(t("admin.invalid_duration", lang))
        return
    if not await punish(message.bot, message.chat.id, target.user_id, "mute", seconds):
        await message.reply(t("common.error", lang))
        return
    await message.reply(
        t(
            "admin.tmuted",
            lang,
            user=target.html,
            duration=humanize_duration(seconds),
            reason_label=t("common.reason", lang),
            reason=_reason(lang, args, target.consumed_args + 1),
        )
    )


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "mute") or not await _bot_needs(
        message, lang, "can_restrict_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    try:
        await message.bot.restrict_chat_member(
            message.chat.id, target.user_id, permissions=ChatPermissions(**UNMUTED_PERMISSIONS)
        )
    except TelegramAPIError:
        await message.reply(t("common.error", lang))
        return
    await message.reply(t("admin.unmuted", lang, user=target.html))


@router.message(Command("promote"))
async def cmd_promote(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "promote") or not await _bot_needs(
        message, lang, "can_promote_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await _pick_target(message, db, lang, args, protect_admins=False)
    if target is None:
        return
    try:
        await message.bot.promote_chat_member(
            message.chat.id,
            target.user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_video_chats=True,
        )
    except TelegramAPIError:
        await message.reply(t("common.error", lang))
        return
    await message.reply(t("admin.promoted", lang, user=target.html))


@router.message(Command("demote"))
async def cmd_demote(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "promote") or not await _bot_needs(
        message, lang, "can_promote_members"
    ):
        return
    args = split_command_args(message.text or message.caption)
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    try:
        await message.bot.promote_chat_member(
            message.chat.id,
            target.user_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_video_chats=False,
            can_change_info=False,
        )
    except TelegramAPIError:
        await message.reply(t("common.error", lang))
        return
    await message.reply(t("admin.demoted", lang, user=target.html))


@router.message(Command("pin"))
async def cmd_pin(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "pin") or not await _bot_needs(
        message, lang, "can_pin_messages"
    ):
        return
    if message.reply_to_message is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    args = split_command_args(message.text or "")
    silent = bool(args) and args[0].lower() in {"silent", "quiet", "off"}
    try:
        await message.bot.pin_chat_message(
            message.chat.id, message.reply_to_message.message_id, disable_notification=silent
        )
    except TelegramAPIError:
        await message.reply(t("common.error", lang))
        return
    await message.reply(t("admin.pinned", lang))


@router.message(Command("unpin"))
async def cmd_unpin(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "pin") or not await _bot_needs(
        message, lang, "can_pin_messages"
    ):
        return
    try:
        if message.reply_to_message is not None:
            await message.bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
        else:
            await message.bot.unpin_chat_message(message.chat.id)
    except TelegramAPIError:
        await message.reply(t("common.error", lang))
        return
    await message.reply(t("admin.unpinned", lang))


@router.message(Command("del"))
async def cmd_del(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "delete") or not await _bot_needs(
        message, lang, "can_delete_messages"
    ):
        return
    if message.reply_to_message is None:
        await message.reply(t("common.reply_or_username", lang))
        return
    try:
        await message.reply_to_message.delete()
        await message.delete()
    except TelegramBadRequest:
        await message.reply(t("admin.purge_limit", lang))


async def purge_range(bot: Bot, chat_id: int, first_id: int, last_id: int) -> int:
    deleted = 0
    ids = list(range(first_id, last_id + 1))
    for start in range(0, len(ids), PURGE_BATCH):
        batch = ids[start : start + PURGE_BATCH]
        try:
            await bot.delete_messages(chat_id, batch)
            deleted += len(batch)
        except TelegramAPIError:
            for message_id in batch:
                try:
                    await bot.delete_message(chat_id, message_id)
                    deleted += 1
                except TelegramAPIError:
                    continue
    return deleted


@router.message(Command("purge"))
async def cmd_purge(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "delete") or not await _bot_needs(
        message, lang, "can_delete_messages"
    ):
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
    await message.answer(t("admin.purged", lang, count=deleted))


@router.message(Command("info", "whois"))
async def cmd_info(message: Message, lang: str, db: Database, settings: Settings) -> None:
    args = split_command_args(message.text or "")
    target = await resolve_target(message, db, args)
    if target is None and message.from_user is not None:
        target = Target(
            user_id=message.from_user.id, name=message.from_user.full_name, html=mention(message.from_user)
        )
    if target is None:
        await message.reply(t("common.user_not_found", lang))
        return

    member = await get_member(message.bot, message.chat.id, target.user_id)
    status = member.status if member is not None else ChatMemberStatus.LEFT
    level = await privilege_level(message.bot, db, message.chat.id, target.user_id, settings.owner_id)
    chat = await db.get_chat(message.chat.id)
    warns = await db.get_warns(message.chat.id, target.user_id)
    username = ""
    if member is not None and member.user is not None and member.user.username:
        username = f"@{member.user.username}"

    await message.reply(
        t(
            "admin.info",
            lang,
            name=target.html,
            username=clean(username or "-"),
            id=target.user_id,
            level=level,
            status=clean(str(status)),
            warns=len(warns),
            warn_limit=chat.warn_limit,
        )
    )


@router.message(Command("id"))
async def cmd_id(message: Message, lang: str) -> None:
    extra = ""
    if message.reply_to_message is not None and message.reply_to_message.from_user is not None:
        extra = t("admin.id_extra", lang, user_id=message.reply_to_message.from_user.id)
    await message.reply(
        t(
            "admin.id_card",
            lang,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else 0,
            extra=extra,
        )
    )


@router.message(Command("admins", "staff"))
async def cmd_admins(message: Message, lang: str) -> None:
    try:
        members = await message.bot.get_chat_administrators(message.chat.id)
    except TelegramAPIError:
        await message.reply(t("common.error", lang))
        return
    lines = [t("admin.admins_title", lang, chat=chat_title(message.chat))]
    for member in members:
        if member.user.is_bot:
            continue
        marker = "👑" if member.status == ChatMemberStatus.CREATOR else "🛡"
        lines.append(f"{marker} {mention(member.user)}")
    await message.reply("\n".join(lines))


@router.message(Command("link", "invitelink"))
async def cmd_link(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "settings"):
        return
    try:
        link = await message.bot.export_chat_invite_link(message.chat.id)
    except TelegramAPIError:
        await message.reply(t("admin.link_failed", lang))
        return
    await message.reply(t("admin.link", lang, link=clean(link)))
