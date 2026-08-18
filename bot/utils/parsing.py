from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

DURATION_PATTERN = re.compile(r"^(\d+)\s*([smhdw])$", re.IGNORECASE)
DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
USERNAME_PATTERN = re.compile(r"^@?[A-Za-z][A-Za-z0-9_]{3,31}$")


def parse_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = DURATION_PATTERN.match(value.strip())
    if not match:
        return None
    amount = int(match.group(1))
    if amount <= 0:
        return None
    seconds = amount * DURATION_UNITS[match.group(2).lower()]
    return seconds if seconds <= 366 * 86400 else None


def humanize_duration(seconds: int) -> str:
    for unit, label in ((604800, "w"), (86400, "d"), (3600, "h"), (60, "m")):
        if seconds >= unit and seconds % unit == 0:
            return f"{seconds // unit}{label}"
    return f"{seconds}s"


def until_date(seconds: int) -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)


def split_command_args(text: str | None) -> list[str]:
    if not text:
        return []
    parts = text.split()
    return parts[1:] if parts else []


def command_payload(text: str | None) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def is_username(token: str) -> bool:
    return bool(USERNAME_PATTERN.match(token or ""))


def parse_user_token(token: str) -> tuple[int | None, str | None]:
    token = (token or "").strip()
    if not token:
        return None, None
    if token.lstrip("-").isdigit():
        return int(token), None
    if is_username(token):
        return None, token.lstrip("@").lower()
    return None, None


def extract_reason(args: list[str], skip: int = 0) -> str:
    return " ".join(args[skip:]).strip()
