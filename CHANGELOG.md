# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-08-18

The bot is rewritten from scratch on **aiogram v3**. The previous repository state carried no working code, so this release is the first usable version.

### Added

- **Roles and permissions per group** — the owner and every admin are detected automatically when the bot joins a group, and kept in sync from `chat_member` / `my_chat_member` updates and the `/sync` command.
- **Twelve bot-level permissions** (ban, mute, warn, delete, pin, promote, settings, locks, notes, AI switch, alias, permissions) whose defaults derive from each admin's real Telegram rights. `/perms` lets the group owner grant or revoke a single permission with a button; `/mperms` lets admins choose what a member may send.
- **Gemini AI core with an in-Telegram switch** — a live `🧠 AI: ON/OFF` button inside `/settings`, plus `/ai on|off` and an owner-level global switch (`/aiglobal`).
- **Eight interface languages** — English (default), Persian, Arabic, Turkish, Russian, Italian, Chinese and Japanese, selectable per group and per user.
- **Moderation** — ban, timed ban, silent ban, kick, mute, timed mute, unmute, promote, demote, pin, unpin, purge, delete, user cards, chat ids, admin list, invite link.
- **Warnings** with a per-chat limit and configurable action (mute / kick / ban).
- **Notes** (`/save`, `#name`) and **keyword filters**, both supporting media.
- **Content locks** for links, media, photos, videos, stickers, GIFs, forwards, mentions, voice, documents and joining bots.
- **Greetings** with placeholders and service-message cleanup.
- **Antiflood** with a configurable threshold and action.
- **Alias packages** to mention groups of members at once.
- **Reports** via `/report` and `@admin`.
- **Linux CLI commands** — `whoami`, `sudo userdel [-f]`, `clear --terminal`.
- **SQLite storage** via aiosqlite, and middlewares for language resolution, chat registration and error containment.
- **Test suite** — 74 tests covering locale parity, parsing, database round-trips and the real dispatcher driven through a mocked Telegram session.
- Docker image, `.env.example`, and a rewritten README.

### Fixed

- `str(ChatType.SUPERGROUP)` returns `"ChatType.SUPERGROUP"` rather than `"supergroup"` on Python 3.11, which made every group chat look like a private chat and disabled all group commands.
- Router-level filters were passed as classes instead of instances, which raised `TypeError` on every group message.

[2.0.0]: https://github.com/hami9/telegram-linux-bot/releases/tag/v2.0.0
