from __future__ import annotations

import json
import re
from pathlib import Path

from bot.i18n import DEFAULT_LANGUAGE, LANGUAGES, is_rtl, language_name, normalize, t

LOCALES = Path(__file__).resolve().parent.parent / "bot" / "i18n" / "locales"
PLACEHOLDER = re.compile(r"{([a-z_]+)}")


def load(lang: str) -> dict[str, str]:
    with (LOCALES / f"{lang}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def test_every_language_has_a_locale_file():
    for code in LANGUAGES:
        assert (LOCALES / f"{code}.json").is_file()


def test_locales_share_the_same_keys():
    base = set(load(DEFAULT_LANGUAGE))
    for code in LANGUAGES:
        assert set(load(code)) == base, f"{code} key mismatch"


def test_locales_share_the_same_placeholders():
    base = load(DEFAULT_LANGUAGE)
    for code in LANGUAGES:
        translated = load(code)
        for key, value in base.items():
            assert set(PLACEHOLDER.findall(value)) == set(PLACEHOLDER.findall(translated[key])), (
                f"{code}:{key} placeholder mismatch"
            )


def test_translation_formats_values():
    assert "3" in t("warns.limit_set", "en", limit=3)
    assert "3" in t("warns.limit_set", "fa", limit=3)


def test_unknown_key_returns_key():
    assert t("nope.missing", "en") == "nope.missing"


def test_unknown_language_falls_back_to_english():
    assert t("common.done", "xx") == t("common.done", "en")
    assert normalize("pt-BR") == DEFAULT_LANGUAGE
    assert normalize("fa-IR") == "fa"


def test_rtl_flags():
    assert is_rtl("fa") and is_rtl("ar")
    assert not is_rtl("en") and not is_rtl("ja")


def test_language_names_are_native():
    assert language_name("ja") == LANGUAGES["ja"]
