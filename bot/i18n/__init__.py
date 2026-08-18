from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DEFAULT_LANGUAGE = "en"

LANGUAGES: dict[str, str] = {
    "en": "🇬🇧 English",
    "fa": "🇮🇷 فارسی",
    "ar": "🇸🇦 العربية",
    "tr": "🇹🇷 Türkçe",
    "ru": "🇷🇺 Русский",
    "it": "🇮🇹 Italiano",
    "zh": "🇨🇳 中文",
    "ja": "🇯🇵 日本語",
}

RTL_LANGUAGES = frozenset({"fa", "ar"})


@lru_cache(maxsize=None)
def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return {str(key): str(value) for key, value in data.items()}


def is_supported(lang: str | None) -> bool:
    return bool(lang) and str(lang).lower() in LANGUAGES


def normalize(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANGUAGE
    code = str(lang).lower().replace("_", "-").split("-")[0]
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def language_name(lang: str) -> str:
    return LANGUAGES.get(normalize(lang), LANGUAGES[DEFAULT_LANGUAGE])


def is_rtl(lang: str) -> bool:
    return normalize(lang) in RTL_LANGUAGES


def available_keys() -> set[str]:
    return set(_load(DEFAULT_LANGUAGE))


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    code = normalize(lang)
    template = _load(code).get(key) or _load(DEFAULT_LANGUAGE).get(key)
    if template is None:
        return key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return template
