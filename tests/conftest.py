from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import TelegramMethod
from aiogram.types import (
    Chat,
    ChatMemberAdministrator,
    ChatMemberMember,
    ChatMemberOwner,
    Message,
    User,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import Settings  # noqa: E402
from bot.db import Database  # noqa: E402
from bot.services.gemini import GeminiClient  # noqa: E402
from main import build_dispatcher  # noqa: E402

BOT_ID = 999
BOT_USER = User(id=BOT_ID, is_bot=True, first_name="LinuxBot", username="linux_test_bot")
OWNER_ID = 1
ADMIN_ID = 2
MEMBER_ID = 3
GROUP_ID = -1001234567890


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.admins: set[int] = {ADMIN_ID, OWNER_ID, BOT_ID}
        self.creators: set[int] = set()

    async def close(self) -> None:
        return None

    async def stream_content(self, *args: Any, **kwargs: Any):  # pragma: no cover
        yield b""

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None) -> Any:
        self.calls.append(method)
        name = type(method).__name__

        if name == "GetMe":
            return BOT_USER
        if name == "GetChatAdministrators":
            return [self._member(user_id) for user_id in sorted(self.admins | self.creators)]
        if name == "GetChatMember":
            return self._member(getattr(method, "user_id", 0))
        if name in {"SendMessage", "EditMessageText"}:
            return Message(
                message_id=500 + len(self.calls),
                date=0,
                chat=Chat(id=getattr(method, "chat_id", GROUP_ID), type="supergroup"),
                from_user=BOT_USER,
                text=getattr(method, "text", ""),
            )
        return True

    def _member(self, user_id: int) -> Any:
        user = User(
            id=user_id,
            is_bot=user_id == BOT_ID,
            first_name="LinuxBot" if user_id == BOT_ID else f"user{user_id}",
            username=None if user_id == BOT_ID else f"user{user_id}",
        )
        if user_id in self.creators:
            return ChatMemberOwner(status="creator", user=user, is_anonymous=False)
        if user_id in self.admins:
            return ChatMemberAdministrator(
                    status="administrator",
                    user=user,
                    can_be_edited=False,
                    is_anonymous=False,
                    can_manage_chat=True,
                    can_delete_messages=True,
                    can_manage_video_chats=True,
                    can_restrict_members=True,
                    can_promote_members=True,
                    can_change_info=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_post_stories=True,
                    can_edit_stories=True,
                    can_delete_stories=True,
                )
        return ChatMemberMember(status="member", user=user)

    def sent_texts(self) -> list[str]:
        texts = []
        for call in self.calls:
            if type(call).__name__ in {"SendMessage", "EditMessageText"}:
                texts.append(getattr(call, "text", ""))
            elif type(call).__name__ == "AnswerCallbackQuery":
                texts.append(getattr(call, "text", "") or "")
        return texts


@pytest.fixture
def session() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
def bot(session: RecordingSession) -> Bot:
    return Bot(
        token=f"{BOT_ID}:TEST",
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        bot_token=f"{BOT_ID}:TEST",
        owner_id=OWNER_ID,
        gemini_api_key="",
        gemini_model="gemini-2.5-flash",
        db_path=tmp_path / "test.db",
        default_lang="en",
        log_level="INFO",
    )


@pytest_asyncio.fixture
async def db(settings: Settings) -> Database:
    database = Database(settings.db_path)
    await database.connect()
    yield database
    await database.close()


@pytest.fixture(scope="session")
def wired_dispatcher():
    return build_dispatcher()


@pytest_asyncio.fixture
async def dispatcher(wired_dispatcher, db: Database, settings: Settings):
    gemini = GeminiClient(settings.gemini_api_key, settings.gemini_model)
    wired_dispatcher["db"] = db
    wired_dispatcher["settings"] = settings
    wired_dispatcher["gemini"] = gemini
    yield wired_dispatcher
    await gemini.close()
