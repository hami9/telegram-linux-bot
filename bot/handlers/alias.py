from __future__ import annotations

from aiogram import Router
from aiogram.enums import MessageEntityType
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.db import Database
from bot.filters import IsGroup
from bot.i18n import t
from bot.utils.formatting import chunks, clean, mention_id
from bot.utils.parsing import parse_user_token, split_command_args
from bot.utils.permissions import is_admin

router = Router(name="alias")
router.message.filter(IsGroup())

MAX_MEMBERS = 50


async def _collect_members(message: Message, db: Database, tokens: list[str]) -> list[int]:
    members: list[int] = []

    for entity in message.entities or []:
        if entity.type == MessageEntityType.TEXT_MENTION and entity.user is not None:
            members.append(entity.user.id)

    if message.reply_to_message is not None and message.reply_to_message.from_user is not None:
        members.append(message.reply_to_message.from_user.id)

    for token in tokens:
        user_id, username = parse_user_token(token)
        if user_id is None and username is not None:
            user_id = await db.find_user_by_username(username)
        if user_id is not None:
            members.append(user_id)

    return members[:MAX_MEMBERS]


async def _names(db: Database, members: list[int]) -> list[str]:
    rendered: list[str] = []
    for user_id in members:
        rendered.append(mention_id(user_id, await db.get_user_label(user_id)))
    return rendered


@router.message(Command("alias", "package"))
async def cmd_alias(message: Message, lang: str, db: Database, settings: Settings) -> None:
    args = split_command_args(message.text or "")
    action = args[0].lower() if args else ""

    if action == "list":
        names = await db.list_aliases(message.chat.id)
        if not names:
            await message.reply(t("alias.empty", lang))
            return
        listed = "\n".join(f"• <code>{clean(name)}</code>" for name in names)
        await message.reply(f"{t('alias.list_title', lang)}\n{listed}")
        return

    if action == "run":
        if len(args) < 2:
            await message.reply(t("alias.usage", lang))
            return
        name = args[1].lower()
        members = await db.get_alias(message.chat.id, name)
        if members is None:
            await message.reply(t("alias.not_found", lang, name=clean(name)))
            return
        if not members:
            await message.reply(t("alias.no_members", lang, name=clean(name)))
            return
        rendered = await _names(db, members)
        body = f"{t('alias.run_header', lang, name=clean(name))}\n" + " ".join(rendered)
        for part in chunks(body):
            await message.answer(part)
        return

    is_privileged = message.from_user is not None and await is_admin(
        message.bot, db, message.chat.id, message.from_user.id, settings.owner_id
    )

    if action in {"add", "set"}:
        if not is_privileged:
            await message.reply(t("common.no_permission", lang))
            return
        if len(args) < 2:
            await message.reply(t("alias.usage", lang))
            return
        name = args[1].lower()
        existing = await db.get_alias(message.chat.id, name) or []
        members = await _collect_members(message, db, args[2:])
        if not members:
            await message.reply(t("alias.need_members", lang))
            return
        total = await db.set_alias(message.chat.id, name, existing + members)
        await message.reply(t("alias.added", lang, name=clean(name), count=total))
        return

    if action in {"del", "delete", "rm", "remove"}:
        if not is_privileged:
            await message.reply(t("common.no_permission", lang))
            return
        if len(args) < 2:
            await message.reply(t("alias.usage", lang))
            return
        name = args[1].lower()
        if await db.delete_alias(message.chat.id, name):
            await message.reply(t("alias.removed", lang, name=clean(name)))
        else:
            await message.reply(t("alias.not_found", lang, name=clean(name)))
        return

    await message.reply(t("alias.usage", lang))
