from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import Settings, load_settings
from bot.db import Database
from bot.handlers import setup_routers
from bot.i18n import t
from bot.middlewares import ChatRegistryMiddleware, ContextMiddleware, ErrorGuardMiddleware
from bot.services.gemini import GeminiClient

logger = logging.getLogger("linuxbot")

PUBLIC_COMMANDS = (
    ("start", "commands.start"),
    ("help", "commands.help"),
    ("settings", "commands.settings"),
    ("lang", "commands.lang"),
    ("about", "commands.about"),
)


async def set_commands(bot: Bot, lang: str) -> None:
    commands = [BotCommand(command=name, description=t(key, lang)[:250]) for name, key in PUBLIC_COMMANDS]
    await bot.set_my_commands(commands)


def build_dispatcher(
    db: Database | None = None,
    settings: Settings | None = None,
    gemini: GeminiClient | None = None,
) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher["db"] = db
    dispatcher["settings"] = settings
    dispatcher["gemini"] = gemini

    dispatcher.update.outer_middleware(ErrorGuardMiddleware())
    for observer in (dispatcher.message, dispatcher.callback_query):
        observer.outer_middleware(ChatRegistryMiddleware())
        observer.outer_middleware(ContextMiddleware())

    dispatcher.include_router(setup_routers())
    return dispatcher


async def run() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    db = Database(settings.db_path)
    await db.connect()

    gemini = GeminiClient(settings.gemini_api_key, settings.gemini_model)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dispatcher = build_dispatcher(db, settings, gemini)

    try:
        await set_commands(bot, settings.default_lang)
        me = await bot.me()
        logger.info("started as @%s with %s locale", me.username, settings.default_lang)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await gemini.close()
        await db.close()
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("stopped")


if __name__ == "__main__":
    main()
