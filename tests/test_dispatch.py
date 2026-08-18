from __future__ import annotations

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update, User

from bot.db import Database
from bot.i18n import t
from tests.conftest import ADMIN_ID, BOT_USER, GROUP_ID, MEMBER_ID, OWNER_ID, RecordingSession

pytestmark = pytest.mark.asyncio

GROUP = Chat(id=GROUP_ID, type="supergroup", title="Test Lab")
PRIVATE = Chat(id=OWNER_ID, type="private")

counter = {"id": 0}


def user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name=f"user{user_id}", username=f"user{user_id}")


def message(text: str, *, chat: Chat = GROUP, from_id: int = ADMIN_ID, reply: Message | None = None) -> Update:
    counter["id"] += 1
    return Update(
        update_id=counter["id"],
        message=Message(
            message_id=counter["id"],
            date=0,
            chat=chat,
            from_user=user(from_id),
            text=text,
            reply_to_message=reply,
        ),
    )


def callback(data: str, *, chat: Chat = GROUP, from_id: int = ADMIN_ID) -> Update:
    counter["id"] += 1
    return Update(
        update_id=counter["id"],
        callback_query=CallbackQuery(
            id=str(counter["id"]),
            from_user=user(from_id),
            chat_instance="test",
            data=data,
            message=Message(
                message_id=counter["id"],
                date=0,
                chat=chat,
                from_user=BOT_USER,
                text="panel",
            ),
        ),
    )


async def test_start_shows_creator_credit(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    await dispatcher.feed_update(bot, message("/start", chat=PRIVATE, from_id=OWNER_ID))
    assert any("@ham1235i" in text for text in session.sent_texts())


async def test_about_shows_creator_credit(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    await dispatcher.feed_update(bot, message("/about", chat=PRIVATE, from_id=OWNER_ID))
    assert any("@ham1235i" in text for text in session.sent_texts())


async def test_help_menu_opens_a_category(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    await dispatcher.feed_update(bot, message("/help", chat=PRIVATE, from_id=OWNER_ID))
    await dispatcher.feed_update(bot, callback("help:cat:ai", chat=PRIVATE, from_id=OWNER_ID))
    assert any("/ai on" in text for text in session.sent_texts())


async def test_settings_panel_requires_admin(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    await dispatcher.feed_update(bot, message("/settings", from_id=MEMBER_ID))
    assert session.sent_texts()[-1] == t("common.no_permission", "en")


async def test_ai_button_toggles_the_chat_flag(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    await dispatcher.feed_update(bot, message("/settings"))
    assert (await db.get_chat(GROUP_ID)).ai_enabled is False

    await dispatcher.feed_update(bot, callback("s:ai"))
    assert (await db.get_chat(GROUP_ID)).ai_enabled is True

    await dispatcher.feed_update(bot, callback("s:ai"))
    assert (await db.get_chat(GROUP_ID)).ai_enabled is False


async def test_ai_button_is_admin_only(dispatcher: Dispatcher, bot: Bot, db: Database):
    await dispatcher.feed_update(bot, callback("s:ai", from_id=MEMBER_ID))
    assert (await db.get_chat(GROUP_ID)).ai_enabled is False


async def test_ai_command_toggle_and_disabled_notice(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    await dispatcher.feed_update(bot, message("/ai on"))
    assert (await db.get_chat(GROUP_ID)).ai_enabled is True

    await dispatcher.feed_update(bot, message("/ai off"))
    assert (await db.get_chat(GROUP_ID)).ai_enabled is False

    await dispatcher.feed_update(bot, message("/ai how do I list ports?"))
    assert session.sent_texts()[-1] == t("ai.disabled_here", "en")


async def test_ai_without_api_key_reports_it(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    await dispatcher.feed_update(bot, message("/ai on"))
    await dispatcher.feed_update(bot, message("/ai hello"))
    assert session.sent_texts()[-1] == t("ai.not_configured", "en")


async def test_ai_answers_when_enabled(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, monkeypatch
):
    async def fake_ask(self, prompt, lang="en", history=None):
        return f"answer for {prompt} in {lang}"

    monkeypatch.setattr("bot.services.gemini.GeminiClient.ask", fake_ask)
    dispatcher["gemini"].api_key = "test-key"

    await dispatcher.feed_update(bot, message("/ai on"))
    await dispatcher.feed_update(bot, message("/ai list open ports"))
    assert any("answer for list open ports" in text for text in session.sent_texts())


async def test_ai_ignores_plain_group_chatter(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, monkeypatch
):
    async def fake_ask(self, prompt, lang="en", history=None):
        return "should not happen"

    monkeypatch.setattr("bot.services.gemini.GeminiClient.ask", fake_ask)
    dispatcher["gemini"].api_key = "test-key"

    await dispatcher.feed_update(bot, message("/ai on"))
    await dispatcher.feed_update(bot, message("just chatting", from_id=MEMBER_ID))
    assert not any("should not happen" in text for text in session.sent_texts())


async def test_ai_continues_when_replying_to_the_bot(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, monkeypatch
):
    async def fake_ask(self, prompt, lang="en", history=None):
        return "follow-up answer"

    monkeypatch.setattr("bot.services.gemini.GeminiClient.ask", fake_ask)
    dispatcher["gemini"].api_key = "test-key"
    await dispatcher.feed_update(bot, message("/ai on"))

    bot_message = Message(message_id=4242, date=0, chat=GROUP, from_user=BOT_USER, text="terminal ready")
    await dispatcher.feed_update(bot, message("and then?", from_id=MEMBER_ID, reply=bot_message))
    assert any("follow-up answer" in text for text in session.sent_texts())


async def test_locked_content_is_deleted(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    await dispatcher.feed_update(bot, message("/lock link"))
    counter["id"] += 1
    offending = Update(
        update_id=counter["id"],
        message=Message(
            message_id=counter["id"],
            date=0,
            chat=GROUP,
            from_user=user(MEMBER_ID),
            text="join https://example.com now",
            entities=[MessageEntity(type="url", offset=5, length=19)],
        ),
    )
    await dispatcher.feed_update(bot, offending)
    assert any(type(call).__name__ == "DeleteMessage" for call in session.calls)


async def test_antiflood_restricts_the_spammer(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    await dispatcher.feed_update(bot, message("/setflood 3"))
    for _ in range(3):
        await dispatcher.feed_update(bot, message("spam", from_id=MEMBER_ID))
    assert any(type(call).__name__ == "RestrictChatMember" for call in session.calls)


async def test_language_switch_changes_panel_language(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    await dispatcher.feed_update(bot, callback("s:lang:fa"))
    assert (await db.get_chat(GROUP_ID)).lang == "fa"

    await dispatcher.feed_update(bot, message("/settings"))
    assert any("تنظیمات" in text for text in session.sent_texts())


async def test_group_language_applies_to_plain_replies(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    await dispatcher.feed_update(bot, callback("s:lang:tr"))
    await dispatcher.feed_update(bot, message("/settings", from_id=MEMBER_ID))
    assert session.sent_texts()[-1] == t("common.no_permission", "tr")


async def test_private_language_is_per_user(dispatcher: Dispatcher, bot: Bot, db: Database):
    await dispatcher.feed_update(bot, callback("s:lang:ja", chat=PRIVATE, from_id=OWNER_ID))
    assert await db.get_user_lang(OWNER_ID) == "ja"


async def test_warn_flow_reaches_the_limit(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    await db.set_chat_field(GROUP_ID, "warn_limit", 2)
    victim = message("spam", from_id=MEMBER_ID).message

    await dispatcher.feed_update(bot, message("/warn flooding", reply=victim))
    assert len(await db.get_warns(GROUP_ID, MEMBER_ID)) == 1

    await dispatcher.feed_update(bot, message("/warn flooding", reply=victim))
    assert await db.get_warns(GROUP_ID, MEMBER_ID) == []
    assert any("mute" in text for text in session.sent_texts())


async def test_warn_refuses_admin_targets(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    victim = message("hi", from_id=ADMIN_ID).message
    await dispatcher.feed_update(bot, message("/warn", reply=victim, from_id=OWNER_ID))
    assert session.sent_texts()[-1] == t("common.target_is_admin", "en")


async def test_notes_save_and_hashtag_lookup(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    source = message("read the rules", from_id=MEMBER_ID).message
    await dispatcher.feed_update(bot, message("/save rules", reply=source))
    assert await db.list_notes(GROUP_ID) == ["rules"]

    await dispatcher.feed_update(bot, message("#rules", from_id=MEMBER_ID))
    assert "read the rules" in session.sent_texts()


async def test_filter_replies_to_the_keyword(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    source = message("https://t.me/support", from_id=ADMIN_ID).message
    await dispatcher.feed_update(bot, message("/filter help", reply=source))
    await dispatcher.feed_update(bot, message("i need help here", from_id=MEMBER_ID))
    assert "https://t.me/support" in session.sent_texts()


async def test_locks_are_stored_from_the_command(dispatcher: Dispatcher, bot: Bot, db: Database):
    await dispatcher.feed_update(bot, message("/lock sticker"))
    assert "sticker" in await db.get_locks(GROUP_ID)
    await dispatcher.feed_update(bot, message("/unlock sticker"))
    assert await db.get_locks(GROUP_ID) == set()


async def test_alias_add_and_run(dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database):
    await dispatcher.feed_update(bot, message("hello", from_id=MEMBER_ID))
    await dispatcher.feed_update(bot, message(f"/alias add devs {MEMBER_ID}"))
    assert await db.get_alias(GROUP_ID, "devs") == [MEMBER_ID]

    await dispatcher.feed_update(bot, message("/alias run devs", from_id=MEMBER_ID))
    assert any(f'tg://user?id={MEMBER_ID}' in text for text in session.sent_texts())


async def test_whoami_reports_privilege(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    await dispatcher.feed_update(bot, message("whoami", from_id=OWNER_ID))
    assert any("root" in text for text in session.sent_texts())

    await dispatcher.feed_update(bot, message("whoami", from_id=MEMBER_ID))
    assert any("user" in text for text in session.sent_texts())


async def test_owner_only_commands_are_gated(dispatcher: Dispatcher, bot: Bot, session: RecordingSession):
    before = len(session.calls)
    await dispatcher.feed_update(bot, message("/stats", from_id=ADMIN_ID))
    assert not any("Chats:" in text for text in session.sent_texts()[before:])

    await dispatcher.feed_update(bot, message("/stats", from_id=OWNER_ID))
    assert any("Chats:" in text for text in session.sent_texts())
