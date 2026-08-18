from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message, TelegramObject, Update

from bot.config import Settings
from bot.db import Database
from bot.i18n import normalize
from bot.utils.permissions import is_group

logger = logging.getLogger(__name__)


class ContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db: Database = data["db"]
        settings: Settings = data["settings"]
        message: Message | None = None
        if isinstance(event, Message):
            message = event
        elif isinstance(event, CallbackQuery) and isinstance(event.message, Message):
            message = event.message

        user = data.get("event_from_user")
        chat = message.chat if message else None
        if chat is None and isinstance(event, ChatMemberUpdated):
            chat = event.chat

        chat_config = None
        if chat is not None:
            chat_config = await db.get_chat(chat.id)
            data["chat_config"] = chat_config

        lang = settings.default_lang
        if chat is not None and is_group(chat.type) and chat_config is not None and chat_config.lang:
            lang = chat_config.lang
        elif user is not None:
            lang = await db.get_user_lang(user.id) or settings.default_lang
        data["lang"] = normalize(lang)

        if user is not None and not user.is_bot:
            await db.remember_user(user.id, user.full_name, user.username or "")

        return await handler(event, data)


class ChatRegistryMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db: Database = data["db"]
        if isinstance(event, Message) and event.chat is not None:
            group = is_group(event.chat.type)
            await db.ensure_chat(
                event.chat.id,
                event.chat.title or "",
                ai_default=not group,
            )
        return await handler(event, data)


class ErrorGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramAPIError as error:
            update = data.get("event_update")
            update_id = update.update_id if isinstance(update, Update) else "?"
            logger.warning("telegram api error on update %s: %s", update_id, error)
        except Exception:
            logger.exception("unhandled error while processing update")
        return None
