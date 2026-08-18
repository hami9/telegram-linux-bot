from __future__ import annotations

from aiogram import Router

from bot.handlers import (
    about,
    admin,
    ai,
    alias,
    antiflood,
    greetings,
    locks,
    notes,
    owner,
    reports,
    settings_panel,
    start,
    terminal,
    warns,
    watchers,
    wordfilters,
)

ROUTERS: tuple[Router, ...] = (
    start.router,
    about.router,
    settings_panel.router,
    owner.router,
    admin.router,
    warns.router,
    notes.router,
    wordfilters.router,
    locks.router,
    greetings.router,
    antiflood.router,
    alias.router,
    reports.router,
    terminal.router,
    ai.router,
    watchers.router,
)


def setup_routers() -> Router:
    root = Router(name="root")
    for router in ROUTERS:
        root.include_router(router)
    return root
