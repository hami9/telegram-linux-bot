# Security Policy

## Supported versions

| Version | Supported |
| :--- | :--- |
| 2.x | ✅ |
| 1.x | ❌ |

## Reporting a vulnerability

Please do **not** open a public issue for a security problem.

Send the details privately to **[@ham1235i](https://t.me/ham1235i)** on Telegram, or open a [private security advisory](https://github.com/hami9/telegram-linux-bot/security/advisories/new) on GitHub. Include what you found, how to reproduce it, and what an attacker could do with it. You will get an answer as soon as possible.

## Running the bot safely

- Keep `BOT_TOKEN` and `GEMINI_API_KEY` in `.env`, which is git-ignored. Never commit them, and never paste them into an issue or a log.
- If a token leaks, revoke it immediately with `/revoke` in [@BotFather](https://t.me/BotFather) and rotate the Gemini key in Google AI Studio.
- `OWNER_ID` grants every permission in every group. Set it to your own account only.
- The SQLite file under `data/` holds chat settings, notes and warnings. Treat backups of it as sensitive.
- The bot only ever executes Telegram API calls. `whoami`, `sudo userdel` and `clear --terminal` are Telegram commands dressed as shell commands — nothing is run on the host.
