from __future__ import annotations

from dataclasses import dataclass

from aiogram.enums import MessageEntityType
from aiogram.types import Message

from bot.db import Database
from bot.utils.formatting import full_name, mention, mention_id
from bot.utils.parsing import parse_user_token


@dataclass
class Target:
    user_id: int
    name: str
    html: str
    consumed_args: int = 0


async def resolve_target(message: Message, db: Database, args: list[str]) -> Target | None:
    if message.reply_to_message is not None and message.reply_to_message.from_user is not None:
        user = message.reply_to_message.from_user
        return Target(user_id=user.id, name=full_name(user), html=mention(user), consumed_args=0)

    for entity in message.entities or []:
        if entity.type == MessageEntityType.TEXT_MENTION and entity.user is not None:
            return Target(
                user_id=entity.user.id,
                name=full_name(entity.user),
                html=mention(entity.user),
                consumed_args=1,
            )

    if not args:
        return None

    user_id, username = parse_user_token(args[0])
    if user_id is None and username is not None:
        user_id = await db.find_user_by_username(username)
        if user_id is None:
            try:
                chat = await message.bot.get_chat(f"@{username}")
            except Exception:
                return None
            user_id = chat.id
            username = chat.username or username
    if user_id is None:
        return None

    name = f"@{username}" if username else str(user_id)
    return Target(user_id=user_id, name=name, html=mention_id(user_id, name), consumed_args=1)
