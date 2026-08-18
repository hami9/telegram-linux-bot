# Contributing

Thanks for taking the time. This project is free software and every feature stays free — please keep any contribution in that spirit.

## Getting set up

```bash
git clone https://github.com/hami9/telegram-linux-bot.git
cd telegram-linux-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pyflakes
cp .env.example .env
```

You need a bot token from [@BotFather](https://t.me/BotFather) to run it for real; the test suite runs without one.

## Before you open a pull request

```bash
python -m pyflakes bot main.py tests
python -m pytest
```

Both must be clean. The same two commands run in CI on every push and pull request.

## House rules for the code

- **No comments and no docstrings** in `bot/` and `main.py`. Names carry the meaning; if a block needs a comment to be understood, it usually needs to be smaller instead.
- Every user-facing string goes through `t("key", lang)` — never hardcode text in a handler.
- When you add a translation key, add it to **all eight** locale files in `bot/i18n/locales/`. `tests/test_i18n.py` fails otherwise, and it also checks that the `{placeholders}` match across languages.
- Database access lives in `bot/db.py`. Handlers call its methods, they do not write SQL.
- Permission checks go through `require_right(message, db, settings, lang, "<right>")` from `bot/utils/access.py`, never a bare admin check.
- New features get tests. `tests/conftest.py` gives you a mocked Telegram session, so a handler can be driven end to end with `dispatcher.feed_update(...)`.

## Adding a language

1. Copy `bot/i18n/locales/en.json` to `bot/i18n/locales/<code>.json` and translate the values, keeping every key and every `{placeholder}`.
2. Add the code and its native name to `LANGUAGES` in `bot/i18n/__init__.py` (and to `RTL_LANGUAGES` if it is right-to-left).
3. Run `python -m pytest tests/test_i18n.py`.

## Reporting things

Bugs and ideas belong in [Issues](https://github.com/hami9/telegram-linux-bot/issues). For anything security related see [SECURITY.md](SECURITY.md).
