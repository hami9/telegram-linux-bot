from __future__ import annotations

import pytest

from bot.db import Database

pytestmark = pytest.mark.asyncio

CHAT = -100777


async def test_defaults_for_unknown_chat(db: Database):
    chat = await db.get_chat(CHAT)
    assert chat.ai_enabled is False
    assert chat.warn_limit == 3
    assert chat.warn_mode == "mute"
    assert chat.lang is None


async def test_ai_toggle_round_trip(db: Database):
    await db.ensure_chat(CHAT, "group")
    assert await db.toggle_chat_flag(CHAT, "ai_enabled") is True
    assert (await db.get_chat(CHAT)).ai_enabled is True
    assert await db.toggle_chat_flag(CHAT, "ai_enabled") is False
    assert (await db.get_chat(CHAT)).ai_enabled is False


async def test_private_chats_start_with_ai_on(db: Database):
    await db.ensure_chat(555, "private", ai_default=True)
    assert (await db.get_chat(555)).ai_enabled is True
    await db.ensure_chat(555, "private", ai_default=True)
    assert (await db.get_chat(555)).ai_enabled is True


async def test_unknown_chat_field_is_rejected(db: Database):
    with pytest.raises(ValueError):
        await db.set_chat_field(CHAT, "drop table", 1)


async def test_language_settings(db: Database):
    await db.set_chat_field(CHAT, "lang", "fa")
    assert (await db.get_chat(CHAT)).lang == "fa"
    await db.set_user_lang(7, "ja")
    assert await db.get_user_lang(7) == "ja"


async def test_warn_lifecycle(db: Database):
    assert await db.get_warns(CHAT, 7) == []
    await db.add_warn(CHAT, 7, "spam")
    reasons = await db.add_warn(CHAT, 7, "links")
    assert reasons == ["spam", "links"]
    assert await db.remove_warn(CHAT, 7) == ["spam"]
    await db.reset_warns(CHAT, 7)
    assert await db.get_warns(CHAT, 7) == []


async def test_notes_and_filters(db: Database):
    await db.save_note(CHAT, "Rules", "be nice")
    assert (await db.get_note(CHAT, "rules"))["content"] == "be nice"
    assert await db.list_notes(CHAT) == ["rules"]
    assert await db.delete_note(CHAT, "rules") is True
    assert await db.delete_note(CHAT, "rules") is False

    await db.save_filter(CHAT, "Hello", "hi there")
    assert [item["keyword"] for item in await db.list_filters(CHAT)] == ["hello"]
    assert await db.delete_filter(CHAT, "hello") is True


async def test_locks_toggle(db: Database):
    assert await db.toggle_lock(CHAT, "link") is True
    assert "link" in await db.get_locks(CHAT)
    assert await db.toggle_lock(CHAT, "link") is False
    assert await db.get_locks(CHAT) == set()


async def test_alias_members_are_unique(db: Database):
    assert await db.set_alias(CHAT, "devs", [5, 5, 9]) == 2
    assert await db.get_alias(CHAT, "devs") == [5, 9]
    assert await db.get_alias(CHAT, "nope") is None
    assert await db.delete_alias(CHAT, "devs") is True


async def test_sudo_and_globals(db: Database):
    await db.add_sudo(11)
    assert await db.is_sudo(11) is True
    assert await db.list_sudo() == [11]
    await db.remove_sudo(11)
    assert await db.is_sudo(11) is False

    assert await db.ai_globally_enabled() is True
    await db.set_ai_global(False)
    assert await db.ai_globally_enabled() is False


async def test_username_lookup_and_stats(db: Database):
    await db.remember_user(21, "Ada", "AdaL")
    assert await db.find_user_by_username("@adal") == 21
    assert await db.get_user_label(21) == "Ada"

    await db.ensure_chat(CHAT, "group")
    stats = await db.stats()
    assert stats["chats"] >= 1 and stats["users"] >= 1
