from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

CREATOR = "@ham1235i"
CREATOR_URL = "https://t.me/ham1235i"
SOURCE_URL = "https://github.com/hami9/telegram-linux-bot"
BOT_VERSION = "2.0.0"

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int
    gemini_api_key: str
    gemini_model: str
    db_path: Path
    default_lang: str
    log_level: str
    creator: str = CREATOR
    creator_url: str = CREATOR_URL
    source_url: str = SOURCE_URL
    version: str = BOT_VERSION

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key)


def _as_int(value: str | None, fallback: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def load_settings(env_file: str | os.PathLike[str] | None = None) -> Settings:
    load_dotenv(env_file or BASE_DIR / ".env", override=False)

    token = (os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and fill it in.")

    db_path = Path(os.getenv("DB_PATH") or "data/bot.db")
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    from bot.i18n import DEFAULT_LANGUAGE, is_supported

    lang = (os.getenv("DEFAULT_LANG") or DEFAULT_LANGUAGE).strip().lower()
    if not is_supported(lang):
        lang = DEFAULT_LANGUAGE

    return Settings(
        bot_token=token,
        owner_id=_as_int(os.getenv("OWNER_ID")),
        gemini_api_key=(os.getenv("GEMINI_API_KEY") or "").strip(),
        gemini_model=(os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip(),
        db_path=db_path,
        default_lang=lang,
        log_level=(os.getenv("LOG_LEVEL") or "INFO").strip().upper(),
    )
