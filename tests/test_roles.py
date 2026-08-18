from __future__ import annotations

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import (
    ChatMemberAdministrator,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberUpdated,
    Update,
)

from bot.constants import BOT_RIGHTS, ROLE_ADMIN, ROLE_MEMBER, ROLE_OWNER
from bot.db import Database
from bot.i18n import t
from bot.utils.access import effective_rights, resolve_role
from tests.conftest import ADMIN_ID, BOT_USER, GROUP_ID, MEMBER_ID, OWNER_ID, RecordingSession
from tests.test_dispatch import GROUP, callback, counter, message, user

pytestmark = pytest.mark.asyncio


def membership(status: str, target_id: int, previous: str = "left") -> Update:
    counter["id"] += 1
    member = user(target_id) if target_id != 0 else BOT_USER
    new_member = (
        ChatMemberAdministrator(
            status="administrator",
            user=member,
            can_be_edited=False,
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
        )
        if status == "administrator"
        else ChatMemberMember(status="member", user=member)
    )
    previous_member = (
        ChatMemberLeft(status="left", user=member)
        if previous == "left"
        else ChatMemberMember(status="member", user=member)
    )
    payload = {
        "update_id": counter["id"],
        "chat": GROUP,
        "from_user": user(OWNER_ID),
        "date": 0,
        "old_chat_member": previous_member,
        "new_chat_member": new_member,
    }
    key = "my_chat_member" if target_id == 0 else "chat_member"
    return Update(update_id=counter["id"], **{key: ChatMemberUpdated(**{k: v for k, v in payload.items() if k != "update_id"})})


async def test_bot_join_detects_owner_and_admins(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    session.creators = {OWNER_ID}
    await dispatcher.feed_update(bot, membership("member", 0))

    owners = await db.list_roles(GROUP_ID, ROLE_OWNER)
    admins = await db.list_roles(GROUP_ID, ROLE_ADMIN)
    assert [user_id for user_id, _ in owners] == [OWNER_ID]
    assert ADMIN_ID in [user_id for user_id, _ in admins]
    assert any("Owner" in text for text in session.sent_texts())


async def test_promotion_updates_the_stored_role(dispatcher: Dispatcher, bot: Bot, db: Database):
    await dispatcher.feed_update(bot, membership("administrator", MEMBER_ID))
    assert await db.get_role(GROUP_ID, MEMBER_ID) == ROLE_ADMIN

    await dispatcher.feed_update(bot, membership("member", MEMBER_ID, previous="member"))
    assert await db.get_role(GROUP_ID, MEMBER_ID) == ROLE_MEMBER


async def test_demotion_drops_custom_permissions(dispatcher: Dispatcher, bot: Bot, db: Database):
    await db.set_override(GROUP_ID, MEMBER_ID, "ban", False)
    await dispatcher.feed_update(bot, membership("member", MEMBER_ID, previous="member"))
    assert await db.get_overrides(GROUP_ID, MEMBER_ID) == {}


async def test_creator_holds_every_right(bot: Bot, db: Database, session: RecordingSession):
    session.creators = {OWNER_ID}
    rights = await effective_rights(bot, db, GROUP_ID, OWNER_ID, 0)
    assert all(rights.values())
    assert await resolve_role(bot, db, GROUP_ID, OWNER_ID, 0) == ROLE_OWNER


async def test_plain_admin_gets_defaults_without_perms(bot: Bot, db: Database):
    rights = await effective_rights(bot, db, GROUP_ID, ADMIN_ID, 0)
    assert rights["ban"] is True
    assert rights["perms"] is False
    assert await resolve_role(bot, db, GROUP_ID, ADMIN_ID, 0) == ROLE_ADMIN


async def test_member_has_no_rights(bot: Bot, db: Database):
    rights = await effective_rights(bot, db, GROUP_ID, MEMBER_ID, 0)
    assert not any(rights.values())
    assert await resolve_role(bot, db, GROUP_ID, MEMBER_ID, 0) == ROLE_MEMBER


async def test_owner_revokes_a_right_and_the_command_stops_working(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    session.creators = {OWNER_ID}
    victim = message("spam", from_id=MEMBER_ID).message

    await dispatcher.feed_update(bot, message(f"/ban {MEMBER_ID}", reply=victim))
    assert any(type(call).__name__ == "BanChatMember" for call in session.calls)

    await dispatcher.feed_update(bot, callback(f"perm:{ADMIN_ID}:ban", from_id=OWNER_ID))
    assert (await db.get_overrides(GROUP_ID, ADMIN_ID))["ban"] is False

    before = len(session.calls)
    await dispatcher.feed_update(bot, message("/ban", reply=victim))
    assert not any(type(call).__name__ == "BanChatMember" for call in session.calls[before:])
    assert session.sent_texts()[-1] == t("roles.no_right", "en", right=t("roles.right_ban", "en"))


async def test_granting_a_right_back_restores_the_command(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    session.creators = {OWNER_ID}
    await db.set_override(GROUP_ID, ADMIN_ID, "ban", False)
    await dispatcher.feed_update(bot, callback(f"perm:{ADMIN_ID}:ban", from_id=OWNER_ID))
    assert (await db.get_overrides(GROUP_ID, ADMIN_ID))["ban"] is True

    victim = message("spam", from_id=MEMBER_ID).message
    await dispatcher.feed_update(bot, message("/ban", reply=victim))
    assert any(type(call).__name__ == "BanChatMember" for call in session.calls)


async def test_plain_admin_cannot_change_permissions(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    session.creators = {OWNER_ID}
    await dispatcher.feed_update(bot, callback(f"perm:{ADMIN_ID}:ban", from_id=ADMIN_ID))
    assert await db.get_overrides(GROUP_ID, ADMIN_ID) == {}
    assert any(t("roles.perms_denied", "en") in text for text in session.sent_texts())


async def test_perms_panel_rejects_non_admin_targets(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
):
    session.creators = {OWNER_ID}
    await dispatcher.feed_update(bot, message(f"/perms {MEMBER_ID}", from_id=OWNER_ID))
    assert session.sent_texts()[-1] == t("roles.perms_not_admin", "en")


async def test_member_permission_panel_restricts(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
):
    await dispatcher.feed_update(bot, message(f"/mperms {MEMBER_ID}"))
    panels = [
        call
        for call in session.calls
        if type(call).__name__ == "SendMessage" and getattr(call, "reply_markup", None) is not None
    ]
    assert panels
    buttons = [button.callback_data for row in panels[-1].reply_markup.inline_keyboard for button in row]
    assert f"mperm:{MEMBER_ID}:media" in buttons

    await dispatcher.feed_update(bot, callback(f"mperm:{MEMBER_ID}:media", from_id=ADMIN_ID))
    restricts = [call for call in session.calls if type(call).__name__ == "RestrictChatMember"]
    assert restricts
    assert restricts[-1].permissions.can_send_photos is False
    assert restricts[-1].permissions.can_send_messages is True


async def test_member_cannot_touch_member_permissions(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
):
    await dispatcher.feed_update(bot, callback(f"mperm:{MEMBER_ID}:media", from_id=MEMBER_ID))
    assert not any(type(call).__name__ == "RestrictChatMember" for call in session.calls)


async def test_staff_list_reports_permission_counts(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession, db: Database
):
    session.creators = {OWNER_ID}
    await dispatcher.feed_update(bot, message("/sync"))
    await dispatcher.feed_update(bot, message("/staff", from_id=MEMBER_ID))
    assert any(f"/{len(BOT_RIGHTS)}" in text for text in session.sent_texts())
