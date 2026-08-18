from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    title TEXT DEFAULT '',
    lang TEXT,
    ai_enabled INTEGER DEFAULT 0,
    warn_limit INTEGER DEFAULT 3,
    warn_mode TEXT DEFAULT 'mute',
    welcome_on INTEGER DEFAULT 0,
    welcome_text TEXT DEFAULT '',
    goodbye_on INTEGER DEFAULT 0,
    goodbye_text TEXT DEFAULT '',
    cleanservice INTEGER DEFAULT 0,
    flood_limit INTEGER DEFAULT 0,
    flood_mode TEXT DEFAULT 'mute',
    updated_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    lang TEXT,
    name TEXT DEFAULT '',
    username TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS warns (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reasons TEXT DEFAULT '[]',
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS notes (
    chat_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    content TEXT DEFAULT '',
    kind TEXT DEFAULT 'text',
    file_id TEXT DEFAULT '',
    PRIMARY KEY (chat_id, name)
);

CREATE TABLE IF NOT EXISTS wordfilters (
    chat_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    content TEXT DEFAULT '',
    kind TEXT DEFAULT 'text',
    file_id TEXT DEFAULT '',
    PRIMARY KEY (chat_id, keyword)
);

CREATE TABLE IF NOT EXISTS locks (
    chat_id INTEGER NOT NULL,
    lock_type TEXT NOT NULL,
    PRIMARY KEY (chat_id, lock_type)
);

CREATE TABLE IF NOT EXISTS aliases (
    chat_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    members TEXT DEFAULT '[]',
    PRIMARY KEY (chat_id, name)
);

CREATE TABLE IF NOT EXISTS sudoers (
    user_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS globals (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);
"""

DEFAULT_CHAT = {
    "title": "",
    "lang": None,
    "ai_enabled": 0,
    "warn_limit": 3,
    "warn_mode": "mute",
    "welcome_on": 0,
    "welcome_text": "",
    "goodbye_on": 0,
    "goodbye_text": "",
    "cleanservice": 0,
    "flood_limit": 0,
    "flood_mode": "mute",
}

CHAT_FIELDS = tuple(DEFAULT_CHAT)


@dataclass
class ChatConfig:
    chat_id: int
    title: str = ""
    lang: str | None = None
    ai_enabled: bool = False
    warn_limit: int = 3
    warn_mode: str = "mute"
    welcome_on: bool = False
    welcome_text: str = ""
    goodbye_on: bool = False
    goodbye_text: str = ""
    cleanservice: bool = False
    flood_limit: int = 0
    flood_mode: str = "mute"


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _fetchone(self, query: str, params: Sequence[Any] = ()) -> aiosqlite.Row | None:
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def _fetchall(self, query: str, params: Sequence[Any] = ()) -> list[aiosqlite.Row]:
        async with self.conn.execute(query, params) as cursor:
            return list(await cursor.fetchall())

    async def _execute(self, query: str, params: Sequence[Any] = ()) -> None:
        await self.conn.execute(query, params)
        await self.conn.commit()

    async def get_chat(self, chat_id: int) -> ChatConfig:
        row = await self._fetchone("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
        if row is None:
            return ChatConfig(chat_id=chat_id)
        return ChatConfig(
            chat_id=chat_id,
            title=row["title"] or "",
            lang=row["lang"],
            ai_enabled=bool(row["ai_enabled"]),
            warn_limit=int(row["warn_limit"] or 3),
            warn_mode=row["warn_mode"] or "mute",
            welcome_on=bool(row["welcome_on"]),
            welcome_text=row["welcome_text"] or "",
            goodbye_on=bool(row["goodbye_on"]),
            goodbye_text=row["goodbye_text"] or "",
            cleanservice=bool(row["cleanservice"]),
            flood_limit=int(row["flood_limit"] or 0),
            flood_mode=row["flood_mode"] or "mute",
        )

    async def ensure_chat(self, chat_id: int, title: str = "", ai_default: bool = False) -> None:
        await self._execute(
            "INSERT INTO chats (chat_id, title, ai_enabled, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title, updated_at = excluded.updated_at",
            (chat_id, title, int(bool(ai_default)), int(time.time())),
        )

    async def set_chat_field(self, chat_id: int, field: str, value: Any) -> None:
        if field not in CHAT_FIELDS:
            raise ValueError(f"unknown chat field: {field}")
        await self.ensure_chat(chat_id)
        if isinstance(value, bool):
            value = int(value)
        await self._execute(f"UPDATE chats SET {field} = ?, updated_at = ? WHERE chat_id = ?", (value, int(time.time()), chat_id))

    async def toggle_chat_flag(self, chat_id: int, field: str) -> bool:
        chat = await self.get_chat(chat_id)
        new_value = not bool(getattr(chat, field))
        await self.set_chat_field(chat_id, field, new_value)
        return new_value

    async def all_chat_ids(self) -> list[int]:
        rows = await self._fetchall("SELECT chat_id FROM chats")
        return [int(row["chat_id"]) for row in rows]

    async def remember_user(self, user_id: int, name: str = "", username: str = "") -> None:
        await self._execute(
            "INSERT INTO users (user_id, name, username) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET name = excluded.name, username = excluded.username",
            (user_id, name, username or ""),
        )

    async def get_user_lang(self, user_id: int) -> str | None:
        row = await self._fetchone("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        return row["lang"] if row else None

    async def set_user_lang(self, user_id: int, lang: str) -> None:
        await self._execute(
            "INSERT INTO users (user_id, lang) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang",
            (user_id, lang),
        )

    async def get_user_label(self, user_id: int) -> str:
        row = await self._fetchone("SELECT name, username FROM users WHERE user_id = ?", (user_id,))
        if row is None:
            return str(user_id)
        name = row["name"] or ""
        username = row["username"] or ""
        return name or (f"@{username}" if username else str(user_id))

    async def find_user_by_username(self, username: str) -> int | None:
        row = await self._fetchone(
            "SELECT user_id FROM users WHERE lower(username) = ?", (username.lstrip("@").lower(),)
        )
        return int(row["user_id"]) if row else None

    async def get_warns(self, chat_id: int, user_id: int) -> list[str]:
        row = await self._fetchone(
            "SELECT reasons FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
        )
        if row is None:
            return []
        try:
            data = json.loads(row["reasons"])
        except (TypeError, ValueError):
            return []
        return [str(item) for item in data] if isinstance(data, list) else []

    async def add_warn(self, chat_id: int, user_id: int, reason: str) -> list[str]:
        reasons = await self.get_warns(chat_id, user_id)
        reasons.append(reason)
        await self._execute(
            "INSERT INTO warns (chat_id, user_id, reasons) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET reasons = excluded.reasons",
            (chat_id, user_id, json.dumps(reasons, ensure_ascii=False)),
        )
        return reasons

    async def remove_warn(self, chat_id: int, user_id: int) -> list[str]:
        reasons = await self.get_warns(chat_id, user_id)
        if reasons:
            reasons.pop()
        await self._execute(
            "INSERT INTO warns (chat_id, user_id, reasons) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET reasons = excluded.reasons",
            (chat_id, user_id, json.dumps(reasons, ensure_ascii=False)),
        )
        return reasons

    async def reset_warns(self, chat_id: int, user_id: int) -> None:
        await self._execute("DELETE FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))

    async def save_note(self, chat_id: int, name: str, content: str, kind: str = "text", file_id: str = "") -> None:
        await self._execute(
            "INSERT INTO notes (chat_id, name, content, kind, file_id) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(chat_id, name) DO UPDATE SET content = excluded.content, kind = excluded.kind, file_id = excluded.file_id",
            (chat_id, name.lower(), content, kind, file_id),
        )

    async def get_note(self, chat_id: int, name: str) -> dict[str, str] | None:
        row = await self._fetchone(
            "SELECT content, kind, file_id FROM notes WHERE chat_id = ? AND name = ?", (chat_id, name.lower())
        )
        if row is None:
            return None
        return {"content": row["content"] or "", "kind": row["kind"] or "text", "file_id": row["file_id"] or ""}

    async def delete_note(self, chat_id: int, name: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM notes WHERE chat_id = ? AND name = ?", (chat_id, name.lower())
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def list_notes(self, chat_id: int) -> list[str]:
        rows = await self._fetchall("SELECT name FROM notes WHERE chat_id = ? ORDER BY name", (chat_id,))
        return [row["name"] for row in rows]

    async def save_filter(self, chat_id: int, keyword: str, content: str, kind: str = "text", file_id: str = "") -> None:
        await self._execute(
            "INSERT INTO wordfilters (chat_id, keyword, content, kind, file_id) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(chat_id, keyword) DO UPDATE SET content = excluded.content, kind = excluded.kind, file_id = excluded.file_id",
            (chat_id, keyword.lower(), content, kind, file_id),
        )

    async def delete_filter(self, chat_id: int, keyword: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM wordfilters WHERE chat_id = ? AND keyword = ?", (chat_id, keyword.lower())
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def list_filters(self, chat_id: int) -> list[dict[str, str]]:
        rows = await self._fetchall(
            "SELECT keyword, content, kind, file_id FROM wordfilters WHERE chat_id = ? ORDER BY keyword", (chat_id,)
        )
        return [
            {
                "keyword": row["keyword"],
                "content": row["content"] or "",
                "kind": row["kind"] or "text",
                "file_id": row["file_id"] or "",
            }
            for row in rows
        ]

    async def get_locks(self, chat_id: int) -> set[str]:
        rows = await self._fetchall("SELECT lock_type FROM locks WHERE chat_id = ?", (chat_id,))
        return {row["lock_type"] for row in rows}

    async def set_lock(self, chat_id: int, lock_type: str, enabled: bool) -> None:
        if enabled:
            await self._execute(
                "INSERT OR IGNORE INTO locks (chat_id, lock_type) VALUES (?, ?)", (chat_id, lock_type)
            )
        else:
            await self._execute(
                "DELETE FROM locks WHERE chat_id = ? AND lock_type = ?", (chat_id, lock_type)
            )

    async def toggle_lock(self, chat_id: int, lock_type: str) -> bool:
        locks = await self.get_locks(chat_id)
        enabled = lock_type not in locks
        await self.set_lock(chat_id, lock_type, enabled)
        return enabled

    async def set_alias(self, chat_id: int, name: str, members: Iterable[int]) -> int:
        unique = sorted({int(member) for member in members})
        await self._execute(
            "INSERT INTO aliases (chat_id, name, members) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, name) DO UPDATE SET members = excluded.members",
            (chat_id, name.lower(), json.dumps(unique)),
        )
        return len(unique)

    async def get_alias(self, chat_id: int, name: str) -> list[int] | None:
        row = await self._fetchone(
            "SELECT members FROM aliases WHERE chat_id = ? AND name = ?", (chat_id, name.lower())
        )
        if row is None:
            return None
        try:
            data = json.loads(row["members"])
        except (TypeError, ValueError):
            return []
        return [int(item) for item in data] if isinstance(data, list) else []

    async def delete_alias(self, chat_id: int, name: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM aliases WHERE chat_id = ? AND name = ?", (chat_id, name.lower())
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def list_aliases(self, chat_id: int) -> list[str]:
        rows = await self._fetchall("SELECT name FROM aliases WHERE chat_id = ? ORDER BY name", (chat_id,))
        return [row["name"] for row in rows]

    async def add_sudo(self, user_id: int) -> None:
        await self._execute("INSERT OR IGNORE INTO sudoers (user_id) VALUES (?)", (user_id,))

    async def remove_sudo(self, user_id: int) -> None:
        await self._execute("DELETE FROM sudoers WHERE user_id = ?", (user_id,))

    async def list_sudo(self) -> list[int]:
        rows = await self._fetchall("SELECT user_id FROM sudoers")
        return [int(row["user_id"]) for row in rows]

    async def is_sudo(self, user_id: int) -> bool:
        row = await self._fetchone("SELECT 1 FROM sudoers WHERE user_id = ?", (user_id,))
        return row is not None

    async def get_global(self, key: str, default: str = "") -> str:
        row = await self._fetchone("SELECT value FROM globals WHERE key = ?", (key,))
        return row["value"] if row else default

    async def set_global(self, key: str, value: str) -> None:
        await self._execute(
            "INSERT INTO globals (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    async def ai_globally_enabled(self) -> bool:
        return await self.get_global("ai_global", "1") != "0"

    async def set_ai_global(self, enabled: bool) -> None:
        await self.set_global("ai_global", "1" if enabled else "0")

    async def stats(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for key, query in (
            ("chats", "SELECT COUNT(*) AS c FROM chats"),
            ("users", "SELECT COUNT(*) AS c FROM users"),
            ("notes", "SELECT COUNT(*) AS c FROM notes"),
            ("filters", "SELECT COUNT(*) AS c FROM wordfilters"),
            ("aliases", "SELECT COUNT(*) AS c FROM aliases"),
            ("ai_chats", "SELECT COUNT(*) AS c FROM chats WHERE ai_enabled = 1"),
        ):
            row = await self._fetchone(query)
            result[key] = int(row["c"]) if row else 0
        return result
