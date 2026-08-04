"""Tests for the remind / reminders / cancel commands."""

import asyncio
import importlib
from datetime import datetime, timezone

import pytest

# The package re-exports the remind *function* as commands.remind, shadowing
# the module attribute — go through importlib to get the module itself
remind_module = importlib.import_module('commands.remind')
from commands.remind import remind
from commands.reminders import reminders
from commands.cancel import cancel
from reminder_manager import ReminderManager
from conftest import make_ctx


@pytest.fixture
def manager(tmp_path):
    return ReminderManager(str(tmp_path / "reminders.json"))


@pytest.fixture
def ctx(manager):
    return make_ctx(reminder_manager=manager)


class FixedDatetime(datetime):
    """datetime whose now() is pinned to 2026-01-01 12:00."""

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 1, 1, 12, 0, 0, tzinfo=tz or timezone.utc)


# --- remind ---

def test_remind_relative(ctx, manager):
    response = asyncio.run(remind(ctx, "5m check the oven"))
    assert "i'll remind you in 5m" in response
    assert "check the oven" in response
    assert len(manager.reminders) == 1
    assert manager.reminders[0].user_id == 42


def test_remind_combined_duration(ctx, manager):
    response = asyncio.run(remind(ctx, "1h30m meeting"))
    assert "in 1h 30m" in response
    assert len(manager.reminders) == 1


def test_remind_other_user(ctx, manager):
    response = asyncio.run(remind(ctx, "<@999> 10m your turn"))
    assert "<@999>" in response
    assert manager.reminders[0].user_id == 999


def test_remind_absolute_time(ctx, manager, monkeypatch):
    monkeypatch.setattr(remind_module, 'datetime', FixedDatetime)
    response = asyncio.run(remind(ctx, "at 5pm dinner time"))
    assert "at 17:00" in response
    assert len(manager.reminders) == 1
    # Due 5 hours after the pinned noon
    expected_due = FixedDatetime.now(timezone.utc).timestamp() + 5 * 3600
    assert manager.reminders[0].due_time == pytest.approx(expected_due)


def test_remind_absolute_bare_hour_rejected(ctx, manager):
    response = asyncio.run(remind(ctx, "at 5 dinner"))
    assert "invalid time" in response
    assert len(manager.reminders) == 0


def test_remind_invalid_duration(ctx, manager):
    response = asyncio.run(remind(ctx, "5x nope"))
    assert "invalid time format" in response
    assert len(manager.reminders) == 0


def test_remind_too_short(ctx, manager):
    response = asyncio.run(remind(ctx, "5s too soon"))
    assert "minimum" in response
    assert len(manager.reminders) == 0


def test_remind_too_long(ctx, manager):
    response = asyncio.run(remind(ctx, "400d far future"))
    assert "maximum" in response


def test_remind_no_args_shows_usage(ctx):
    response = asyncio.run(remind(ctx, ""))
    assert "usage" in response


# --- reminders (list) ---

def test_reminders_empty(ctx):
    response = asyncio.run(reminders(ctx, ""))
    assert "no pending reminders" in response


def test_reminders_listed_soonest_first(ctx, manager):
    now = datetime.now(timezone.utc).timestamp()
    manager.add_reminder(user_id=42, channel_id=100, message="later", due_time=now + 7200)
    manager.add_reminder(user_id=42, channel_id=100, message="sooner", due_time=now + 600)
    response = asyncio.run(reminders(ctx, ""))
    lines = response.split("\n")
    assert "1." in lines[1] and "sooner" in lines[1]
    assert "2." in lines[2] and "later" in lines[2]


def test_reminders_only_shows_own(ctx, manager):
    now = datetime.now(timezone.utc).timestamp()
    manager.add_reminder(user_id=999, channel_id=100, message="not yours", due_time=now + 600)
    response = asyncio.run(reminders(ctx, ""))
    assert "no pending reminders" in response


# --- cancel ---

def test_cancel_by_number(ctx, manager):
    now = datetime.now(timezone.utc).timestamp()
    manager.add_reminder(user_id=42, channel_id=100, message="keep", due_time=now + 7200)
    manager.add_reminder(user_id=42, channel_id=100, message="drop", due_time=now + 600)
    response = asyncio.run(cancel(ctx, "1"))  # soonest = "drop"
    assert "drop" in response
    assert len(manager.reminders) == 1
    assert manager.reminders[0].message == "keep"


def test_cancel_all(ctx, manager):
    now = datetime.now(timezone.utc).timestamp()
    manager.add_reminder(user_id=42, channel_id=100, message="a", due_time=now + 600)
    manager.add_reminder(user_id=42, channel_id=100, message="b", due_time=now + 700)
    response = asyncio.run(cancel(ctx, "all"))
    assert "cancelled 2" in response
    assert len(manager.reminders) == 0


def test_cancel_out_of_range(ctx, manager):
    now = datetime.now(timezone.utc).timestamp()
    manager.add_reminder(user_id=42, channel_id=100, message="a", due_time=now + 600)
    response = asyncio.run(cancel(ctx, "5"))
    assert "no reminder number 5" in response
    assert len(manager.reminders) == 1


def test_cancel_invalid_arg(ctx, manager):
    now = datetime.now(timezone.utc).timestamp()
    manager.add_reminder(user_id=42, channel_id=100, message="a", due_time=now + 600)
    response = asyncio.run(cancel(ctx, "xyz"))
    assert "usage" in response


def test_cancel_no_reminders(ctx):
    response = asyncio.run(cancel(ctx, "1"))
    assert "no pending reminders" in response
