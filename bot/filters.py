from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.db import Database
from bot.utils.permissions import is_admin, is_group


class IsGroup(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.chat is not None and is_group(message.chat.type)


class IsPrivate(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.chat is not None and not is_group(message.chat.type)


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, db: Database, settings: Settings) -> bool:
        if message.from_user is None or message.chat is None:
            return False
        if not is_group(message.chat.type):
            return True
        return await is_admin(message.bot, db, message.chat.id, message.from_user.id, settings.owner_id)


class IsAdminCallback(BaseFilter):
    async def __call__(self, callback: CallbackQuery, db: Database, settings: Settings) -> bool:
        message = callback.message
        if callback.from_user is None or message is None or message.chat is None:
            return False
        if not is_group(message.chat.type):
            return True
        return await is_admin(callback.bot, db, message.chat.id, callback.from_user.id, settings.owner_id)


class IsOwner(BaseFilter):
    async def __call__(self, message: Message, settings: Settings) -> bool:
        return message.from_user is not None and message.from_user.id == settings.owner_id
