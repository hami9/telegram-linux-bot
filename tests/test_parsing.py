from __future__ import annotations

import pytest

from bot.utils.parsing import (
    command_payload,
    humanize_duration,
    is_username,
    parse_duration,
    parse_user_token,
    split_command_args,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("30s", 30), ("10m", 600), ("2h", 7200), ("3d", 259200), ("1w", 604800), ("2 h", 7200)],
)
def test_parse_duration_accepts_units(value, expected):
    assert parse_duration(value) == expected


@pytest.mark.parametrize("value", ["", None, "abc", "10y", "-5m", "0m", "999w"])
def test_parse_duration_rejects_garbage(value):
    assert parse_duration(value) is None


def test_humanize_duration_roundtrip():
    assert humanize_duration(600) == "10m"
    assert humanize_duration(7200) == "2h"
    assert humanize_duration(45) == "45s"


def test_split_command_args_drops_the_command():
    assert split_command_args("/ban @spammer flooding") == ["@spammer", "flooding"]
    assert split_command_args("/ban") == []
    assert split_command_args(None) == []


def test_command_payload_keeps_the_rest():
    assert command_payload("/ai how do I list ports?") == "how do I list ports?"
    assert command_payload("/ai") == ""


def test_parse_user_token():
    assert parse_user_token("12345") == (12345, None)
    assert parse_user_token("@Someone") == (None, "someone")
    assert parse_user_token("not a user") == (None, None)


def test_is_username_rules():
    assert is_username("@valid_name")
    assert not is_username("@ab")
    assert not is_username("1234")
