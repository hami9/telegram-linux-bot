from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import ADMINISTRATOR, IS_NOT_MEMBER, MEMBER, Command, ChatMemberUpdatedFilter
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from bot.config import Settings
from bot.constants import BOT_RIGHTS, MEMBER_PERMISSIONS, ROLE_ADMIN, ROLE_MEMBER, ROLE_OWNER
from bot.db import Database
from bot.filters import IsGroup
from bot.i18n import t
from bot.keyboards import member_perms_keyboard, rights_keyboard
from bot.utils.access import (
    build_permissions,
    current_member_permissions,
    effective_rights,
    require_right,
    resolve_role,
    sync_staff,
)
from bot.utils.formatting import chat_title, mention_id
from bot.utils.parsing import split_command_args
from bot.utils.permissions import bot_can, get_member
from bot.utils.targeting import resolve_target

router = Router(name="roles")

ROLE_KEYS = {
    ROLE_OWNER: "roles.role_owner",
    ROLE_ADMIN: "roles.role_admin",
    ROLE_MEMBER: "roles.role_member",
}


def _state(value: bool, lang: str) -> str:
    return t("common.on", lang) if value else t("common.off", lang)


async def _staff_summary(message: Message, db: Database, lang: str, owner_id: int) -> str:
    chat_id = message.chat.id
    lines = [t("roles.list_title", lang, chat=chat_title(message.chat))]
    for user_id, _ in await db.list_roles(chat_id, ROLE_OWNER):
        lines.append(f"👑 {mention_id(user_id, await db.get_user_label(user_id))}")
    for user_id, _ in await db.list_roles(chat_id, ROLE_ADMIN):
        rights = await effective_rights(message.bot, db, chat_id, user_id, owner_id)
        granted = sum(1 for value in rights.values() if value)
        lines.append(
            f"🛡 {mention_id(user_id, await db.get_user_label(user_id))} — {granted}/{len(BOT_RIGHTS)}"
        )
    return "\n".join(lines)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> (MEMBER | ADMINISTRATOR)))
async def on_bot_added(event: ChatMemberUpdated, lang: str, db: Database) -> None:
    chat = event.chat
    if chat is None or chat.type not in {"group", "supergroup"}:
        return
    await db.ensure_chat(chat.id, chat.title or "")
    owners, admins = await sync_staff(event.bot, db, chat.id)
    if owners < 0:
        try:
            await event.bot.send_message(chat.id, t("roles.sync_failed", lang))
        except TelegramAPIError:
            pass
        return

    owner_ids = await db.list_roles(chat.id, ROLE_OWNER)
    owner_label = "-"
    if owner_ids:
        owner_label = mention_id(owner_ids[0][0], await db.get_user_label(owner_ids[0][0]))
    try:
        await event.bot.send_message(
            chat.id,
            t("roles.intro", lang, chat=chat_title(chat), owner=owner_label, admins=admins),
        )
    except TelegramAPIError:
        pass


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER >> ADMINISTRATOR))
async def on_bot_promoted(event: ChatMemberUpdated, lang: str, db: Database) -> None:
    if event.chat is None:
        return
    owners, admins = await sync_staff(event.bot, db, event.chat.id)
    if owners < 0:
        return
    try:
        await event.bot.send_message(event.chat.id, t("roles.synced", lang, owners=owners, admins=admins))
    except TelegramAPIError:
        pass


@router.chat_member()
async def on_member_changed(event: ChatMemberUpdated, db: Database) -> None:
    if event.chat is None or event.new_chat_member is None:
        return
    user = event.new_chat_member.user
    if user is None or user.is_bot:
        return
    status = event.new_chat_member.status
    if status == ChatMemberStatus.CREATOR:
        role = ROLE_OWNER
    elif status == ChatMemberStatus.ADMINISTRATOR:
        role = ROLE_ADMIN
    else:
        role = ROLE_MEMBER
    await db.remember_user(user.id, user.full_name, user.username or "")
    await db.set_role(event.chat.id, user.id, role)
    if role == ROLE_MEMBER:
        await db.clear_overrides(event.chat.id, user.id)


@router.message(Command("sync", "syncadmins", "refresh"), IsGroup())
async def cmd_sync(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "settings"):
        return
    owners, admins = await sync_staff(message.bot, db, message.chat.id)
    if owners < 0:
        await message.reply(t("roles.sync_failed", lang))
        return
    await message.reply(t("roles.synced", lang, owners=owners, admins=admins))


@router.message(Command("staff", "roles", "adminlist"), IsGroup())
async def cmd_staff(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await db.list_roles(message.chat.id, ROLE_OWNER):
        await sync_staff(message.bot, db, message.chat.id)
    await message.reply(await _staff_summary(message, db, lang, settings.owner_id))


@router.message(Command("perms", "rights", "setperm"), IsGroup())
async def cmd_perms(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "perms"):
        return
    args = split_command_args(message.text or "")
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return

    role = await resolve_role(message.bot, db, message.chat.id, target.user_id, settings.owner_id)
    if role == ROLE_OWNER:
        await message.reply(t("roles.perms_owner", lang))
        return
    if role != ROLE_ADMIN:
        await message.reply(t("roles.perms_not_admin", lang))
        return

    rights = await effective_rights(message.bot, db, message.chat.id, target.user_id, settings.owner_id)
    await message.reply(
        t("roles.perms_title", lang, user=target.html, role=t(ROLE_KEYS[role], lang)),
        reply_markup=rights_keyboard(lang, target.user_id, rights),
    )


@router.callback_query(F.data.startswith("perm:"))
async def cb_toggle_right(callback: CallbackQuery, lang: str, db: Database, settings: Settings) -> None:
    message = callback.message
    parts = (callback.data or "").split(":")
    if not isinstance(message, Message) or len(parts) != 3 or callback.from_user is None:
        await callback.answer(t("common.error", lang), show_alert=True)
        return

    actor_rights = await effective_rights(
        callback.bot, db, message.chat.id, callback.from_user.id, settings.owner_id
    )
    if not actor_rights.get("perms", False):
        await callback.answer(t("roles.perms_denied", lang), show_alert=True)
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    right = parts[2]
    if right not in BOT_RIGHTS:
        await callback.answer(t("common.error", lang), show_alert=True)
        return

    rights = await effective_rights(callback.bot, db, message.chat.id, user_id, settings.owner_id)
    new_value = not rights.get(right, False)
    await db.set_override(message.chat.id, user_id, right, new_value)
    rights[right] = new_value

    try:
        await message.edit_reply_markup(reply_markup=rights_keyboard(lang, user_id, rights))
    except TelegramBadRequest:
        pass
    await callback.answer(
        t("roles.perms_saved", lang, right=t(f"roles.right_{right}", lang), state=_state(new_value, lang))
    )


@router.message(Command("mperms", "memberperms", "restrict"), IsGroup())
async def cmd_member_perms(message: Message, lang: str, db: Database, settings: Settings) -> None:
    if not await require_right(message, db, settings, lang, "mute"):
        return
    if not await bot_can(message.bot, message.chat.id, "can_restrict_members"):
        await message.reply(t("common.need_right", lang, right="can_restrict_members"))
        return

    args = split_command_args(message.text or "")
    target = await resolve_target(message, db, args)
    if target is None:
        await message.reply(t("common.reply_or_username", lang))
        return

    role = await resolve_role(message.bot, db, message.chat.id, target.user_id, settings.owner_id)
    if role != ROLE_MEMBER:
        await message.reply(t("roles.member_is_admin", lang))
        return

    member = await get_member(message.bot, message.chat.id, target.user_id)
    allowed = current_member_permissions(member)
    await message.reply(
        t("roles.member_title", lang, user=target.html),
        reply_markup=member_perms_keyboard(lang, target.user_id, allowed),
    )


@router.callback_query(F.data.startswith("mperm:"))
async def cb_toggle_member_perm(
    callback: CallbackQuery, lang: str, db: Database, settings: Settings
) -> None:
    message = callback.message
    parts = (callback.data or "").split(":")
    if not isinstance(message, Message) or len(parts) != 3 or callback.from_user is None:
        await callback.answer(t("common.error", lang), show_alert=True)
        return

    actor_rights = await effective_rights(
        callback.bot, db, message.chat.id, callback.from_user.id, settings.owner_id
    )
    if not actor_rights.get("mute", False):
        await callback.answer(t("common.admin_only_button", lang), show_alert=True)
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await callback.answer(t("common.error", lang), show_alert=True)
        return
    name = parts[2]
    if name not in MEMBER_PERMISSIONS:
        await callback.answer(t("common.error", lang), show_alert=True)
        return

    member = await get_member(callback.bot, message.chat.id, user_id)
    allowed = current_member_permissions(member)
    allowed[name] = not allowed.get(name, True)

    try:
        await callback.bot.restrict_chat_member(
            message.chat.id, user_id, permissions=build_permissions(allowed)
        )
    except TelegramAPIError:
        await callback.answer(t("common.error", lang), show_alert=True)
        return

    try:
        await message.edit_reply_markup(reply_markup=member_perms_keyboard(lang, user_id, allowed))
    except TelegramBadRequest:
        pass
    await callback.answer(
        t(
            "roles.member_saved",
            lang,
            perm=t(f"roles.perm_{name}", lang),
            state=_state(allowed[name], lang),
        )
    )
