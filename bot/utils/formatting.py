from __future__ import annotations

from html import escape

from aiogram.types import Chat, User

MAX_MESSAGE_LENGTH = 4000


def clean(value: str | None) -> str:
    return escape(str(value or ""), quote=False)


def full_name(user: User | None) -> str:
    if user is None:
        return "unknown"
    name = " ".join(part for part in (user.first_name, user.last_name) if part)
    return name or (user.username or str(user.id))


def mention(user: User | None) -> str:
    if user is None:
        return "unknown"
    return f'<a href="tg://user?id={user.id}">{clean(full_name(user))}</a>'


def mention_id(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{clean(name)}</a>'


def chat_title(chat: Chat | None) -> str:
    if chat is None:
        return "chat"
    return clean(chat.title or chat.full_name or str(chat.id))


def chunks(text: str, size: int = MAX_MESSAGE_LENGTH) -> list[str]:
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= size:
            parts.append(remaining)
            break
        cut = remaining.rfind("\n", 0, size)
        if cut <= 0:
            cut = size
        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    return parts


def render_template(template: str, *, user: User, chat: Chat, count: int | None = None) -> str:
    values = {
        "mention": mention(user),
        "first": clean(user.first_name),
        "last": clean(user.last_name or ""),
        "username": clean(f"@{user.username}") if user.username else clean(full_name(user)),
        "id": str(user.id),
        "chatname": chat_title(chat),
        "count": str(count if count is not None else ""),
    }
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return template
