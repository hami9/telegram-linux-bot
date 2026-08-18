# 🐧 Telegram Linux Terminal Bot

[![CI](https://github.com/hami9/telegram-linux-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/hami9/telegram-linux-bot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-v3-2CA5E0.svg?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Languages](https://img.shields.io/badge/languages-8-orange.svg)](#-features)
[![Free forever](https://img.shields.io/badge/price-free%20forever-brightgreen.svg)](#-credits)

A complete Telegram group management bot with a Linux command-line feel, built with Python and **aiogram v3**. It ships moderation, warnings, notes, filters, locks, greetings and antiflood — plus a **Gemini AI core you can switch on and off from a button inside Telegram**, and an interface available in **8 languages**.

Everything is free, forever. No premium tier, no paid features, no hidden gates. The source is public.

👤 Created by **[@ham1235i](https://t.me/ham1235i)**

---

## 🚀 Features

* **🔑 Automatic roles per group** — the moment the bot joins a group it reads the member list and recognises the **owner** and every **admin** on its own, then keeps that in sync whenever someone is promoted, demoted or leaves. Each admin starts with permissions derived from their real Telegram rights; the group owner can grant or revoke any single one with a button, and admins can adjust what a member is allowed to send.
* **🧠 AI core with an in-Telegram switch** — `/settings` opens an inline panel with a live `🧠 AI: ON/OFF` button. One tap flips the AI for that chat and the panel redraws itself. `/ai on` and `/ai off` do the same from text, and the bot owner has a global kill switch.
* **🌐 8 interface languages** — English (default), فارسی, العربية, Türkçe, Русский, Italiano, 中文, 日本語. Admins set the language per group; each user can set their own in private chat. AI answers follow the chat's language.
* **🛡 Full moderation** — ban, timed ban, silent ban, kick, mute, timed mute, promote, demote, pin, purge, user cards.
* **⚠️ Warning system** — per-chat limit and a configurable action (mute / kick / ban) when a member hits it.
* **📝 Notes & filters** — save messages or media as `#notes`, and auto-reply to keywords.
* **🔒 Content locks** — links, media, photos, videos, stickers, GIFs, forwards, mentions, voice, documents and joining bots.
* **👋 Greetings** — welcome and goodbye messages with placeholders, plus service-message cleanup.
* **🌊 Antiflood** — act after N consecutive messages from the same member.
* **👥 Alias packages** — group members under a name (`devs`, `mods`) and mention them all at once.
* **💻 Linux CLI flavour** — `whoami`, `sudo userdel -f @user` and `clear --terminal` work as real commands.

---

## 💻 Command reference

### Moderation
| Command | Action |
| :--- | :--- |
| `/ban`, `/sban`, `/tban 10m` | Ban, silent ban, timed ban |
| `/unban` | Lift a ban |
| `/kick`, `/kickme` | Remove a user, or leave yourself |
| `/mute`, `/tmute 30m`, `/unmute` | Mute controls |
| `/promote`, `/demote` | Admin controls |
| `/pin`, `/unpin` | Pin controls |
| `/purge`, `/del` | Delete up to the replied message, or just it |
| `/info`, `/id`, `/admins`, `/link` | Chat and user information |

### Roles & permissions
| Command | Action | Who |
| :--- | :--- | :--- |
| `/staff` | Owner and admins with how many permissions each holds | Everyone |
| `/sync` | Read the admin list from Telegram again | Settings permission |
| `/perms` | Panel to grant or revoke a single permission of an admin | Group owner |
| `/mperms` | Panel to allow or block what a member may send | Mute permission |

Permissions: `Ban` · `Mute` · `Warn` · `Delete` · `Pin` · `Promote` · `Settings` · `Locks` · `Notes` · `AI switch` · `Alias` · `Permissions`

Defaults come from the admin's own Telegram rights — an admin without *ban users* in Telegram does not get the bot's Ban permission either. `Permissions` is off by default and only the group creator (or the bot owner) holds it, until they hand it to someone else. Every override is per group, and it is dropped automatically when the person stops being an admin.

Member permissions map onto Telegram's own restrictions: `Messages`, `Media`, `Stickers & GIFs`, `Polls`, `Link previews`, `Invite`, `Pin`, `Chat info`.

### Warnings
`/warn` · `/dwarn` · `/unwarn` · `/resetwarn` · `/warns` · `/warnlimit 3` · `/warnmode mute|kick|ban`

### Notes & filters
`/save name` · `/get name` · `#name` · `/notes` · `/clear name` · `/filter word` · `/filters` · `/stop word`

### Locks
`/lock <type>` · `/unlock <type>` · `/locks`
Types: `link`, `media`, `photo`, `video`, `sticker`, `gif`, `forward`, `mention`, `voice`, `document`, `bots`

### Greetings
`/welcome on|off` · `/goodbye on|off` · `/setwelcome <text>` · `/setgoodbye <text>` · `/cleanservice on|off`
Placeholders: `{mention}` `{first}` `{last}` `{username}` `{id}` `{chatname}` `{count}`

### Antiflood
`/antiflood` · `/setflood 10` · `/setflood off` · `/setfloodmode mute|kick|ban`

### AI
| Command | Action | Who |
| :--- | :--- | :--- |
| `/ai <prompt>` | Ask the AI core | Everyone |
| `/ai on`, `/ai off` | Turn the AI on or off in this chat | Admins |
| `/settings` → 🧠 button | The same switch, as a button | Admins |
| `/aiglobal on\|off` | Global switch for every chat | Bot owner |

When the AI is on, replying to one of the bot's messages continues the conversation. In private chat the AI is on by default; in groups it starts off.

### Alias packages
`/alias add devs @user1 @user2` · `/alias run devs` · `/alias del devs` · `/alias list`

### Misc
`/start` · `/help` · `/settings` · `/lang` · `/report` (or `@admin`) · `/about`

### Linux style
| Terminal | Effect |
| :--- | :--- |
| `whoami` | Your identity, chat id and privilege (`root` / `sudoers` / `user`) |
| `sudo userdel @user` | Kick that user |
| `sudo userdel -f @user` | Ban that user |
| `clear --terminal` | Purge messages up to the replied one |

### Owner only
`/sudo add|del|list` · `/stats` · `/aiglobal` · `/broadcast <text>`

---

## ⚙️ Installation

### 1. Clone and install

```bash
git clone https://github.com/hami9/telegram-linux-bot.git
cd telegram-linux-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

| Variable | Meaning |
| :--- | :--- |
| `BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) — required |
| `OWNER_ID` | Your numeric Telegram id (send `/id` to the bot) |
| `GEMINI_API_KEY` | Key from [Google AI Studio](https://aistudio.google.com/apikey) — optional; without it every other feature still works and only the AI replies that it is not configured |
| `GEMINI_MODEL` | Defaults to `gemini-2.5-flash` |
| `DB_PATH` | SQLite file, defaults to `data/bot.db` |
| `DEFAULT_LANG` | `en`, `fa`, `ar`, `tr`, `ru`, `it`, `zh` or `ja` |
| `LOG_LEVEL` | `INFO`, `DEBUG`, … |

In [@BotFather](https://t.me/BotFather) turn **Group Privacy off** (`/setprivacy` → Disable) so the bot can see group messages.

### 3. Run

```bash
python main.py
```

Then add the bot to your group, promote it to admin with *delete messages*, *ban users* and *pin messages*, and run `/settings`.

### Docker

```bash
docker build -t linux-terminal-bot .
docker run -d --name linuxbot --env-file .env -v "$PWD/data:/app/data" --restart unless-stopped linux-terminal-bot
```

### systemd

```ini
[Unit]
Description=Telegram Linux Terminal Bot
After=network.target

[Service]
WorkingDirectory=/opt/telegram-linux-bot
ExecStart=/opt/telegram-linux-bot/.venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🧪 Tests

```bash
pip install pytest pytest-asyncio
python -m pytest
```

The suite checks that all 8 locales carry the same keys and placeholders, that durations and user targets parse correctly, that the database round-trips every setting, and it drives the real dispatcher through a mocked Telegram session — role detection on join, granting and revoking an admin permission, member restrictions, the AI toggle, language switching, warnings, notes, filters, locks and antiflood all run end to end.

---

## 🗂 Project layout

```
main.py                  entrypoint and dispatcher wiring
bot/config.py            environment settings
bot/db.py                SQLite storage
bot/middlewares.py       language resolution, chat registry, error guard
bot/filters.py           admin / group / owner filters
bot/keyboards.py         inline panels
bot/constants.py         locks, modes, permission sets
bot/i18n/                translation loader and the 8 locale files
bot/services/            Gemini client and rate limiting
bot/handlers/            one module per feature (roles.py holds the role sync and permission panels)
bot/utils/access.py      role resolution, effective permissions, staff sync
tests/                   pytest suite
```

---

## 🇮🇷 راهنمای سریع فارسی

۱. مخزن را کلون کن و `pip install -r requirements.txt` را اجرا کن.
۲. فایل `.env.example` را به `.env` کپی کن و `BOT_TOKEN` و `OWNER_ID` را بگذار. اگر کلید `GEMINI_API_KEY` را هم بگذاری، هسته‌ی هوش مصنوعی فعال می‌شود.
۳. با `python main.py` ربات را بالا بیاور.
۴. ربات را به گروه اضافه کن، ادمینش کن و `/settings` را بزن؛ از همان‌جا با یک دکمه هوش مصنوعی را روشن یا خاموش کن و زبان گروه را از بین ۸ زبان انتخاب کن.
۵. ربات به‌محض ورود، اونر و ادمین‌های گروه را خودش می‌شناسد. اونر با `/perms` می‌تواند دسترسی هر ادمین را تک‌به‌تک کم یا زیاد کند و ادمین‌ها با `/mperms` تعیین می‌کنند یک ممبر چه چیزی بفرستد. `/staff` هم لیست کادر مدیریت را نشان می‌دهد.

---

## 🤝 Contributing

Pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the setup, the house rules and how to add a language. Bugs and ideas go to [Issues](https://github.com/hami9/telegram-linux-bot/issues); security reports follow [SECURITY.md](SECURITY.md).

Changes per version are listed in [CHANGELOG.md](CHANGELOG.md).

---

## 📄 License

Released under the [MIT License](LICENSE) — use it, change it, host it, sell nothing back to your users for it.

---

## 📜 Credits

Made by **[@ham1235i](https://t.me/ham1235i)** — free and open source, every feature, for everyone.
