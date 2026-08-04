"""Tests for reminder time parsing (relative, combined, and clock times)."""

from datetime import datetime, timezone

from commands.remind import parse_time, parse_clock_time


# --- relative / combined durations ---

def test_single_units():
    assert parse_time("45s") == 45
    assert parse_time("5m") == 300
    assert parse_time("2h") == 7200
    assert parse_time("1d") == 86400


def test_combined_units():
    assert parse_time("1h30m") == 5400
    assert parse_time("2d4h") == 187200
    assert parse_time("1d2h3m4s") == 93784


def test_case_insensitive():
    assert parse_time("5M") == 300
    assert parse_time("1H30M") == 5400


def test_invalid_durations():
    assert parse_time("5x") is None
    assert parse_time("m5") is None
    assert parse_time("1h30") is None
    assert parse_time("") is None
    assert parse_time("soon") is None


# --- clock times ---

NOON = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_clock_24h():
    assert parse_clock_time("17:30", NOON) == 5 * 3600 + 30 * 60


def test_clock_pm():
    assert parse_clock_time("5pm", NOON) == 5 * 3600


def test_clock_pm_with_minutes():
    assert parse_clock_time("5:30pm", NOON) == 5 * 3600 + 30 * 60


def test_clock_12pm_is_noon_next_day():
    # Exactly now -> next occurrence is tomorrow
    assert parse_clock_time("12pm", NOON) == 24 * 3600


def test_clock_earlier_time_rolls_to_tomorrow():
    assert parse_clock_time("11am", NOON) == 23 * 3600


def test_clock_12am_is_midnight():
    assert parse_clock_time("12am", NOON) == 12 * 3600


def test_clock_bare_hour_rejected():
    # "at 5" is ambiguous (5am or 5pm?)
    assert parse_clock_time("5", NOON) is None


def test_clock_invalid():
    assert parse_clock_time("25:00", NOON) is None
    assert parse_clock_time("13pm", NOON) is None
    assert parse_clock_time("5:75pm", NOON) is None
    assert parse_clock_time("dinner", NOON) is None
