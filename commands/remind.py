"""Reminder command implementation."""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING
from zoneinfo import ZoneInfo
from config import REMINDER_MIN_TIME_SECONDS, REMINDER_MAX_TIME_SECONDS, REMINDER_TIMEZONE
from utils import format_duration_long

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)

# Relative durations: one or more <number><unit> parts, e.g. 5m, 1h30m, 2d4h
TIME_FULL_RE = re.compile(r'^(?:\d+[smhd])+$', re.I)
TIME_PART_RE = re.compile(r'(\d+)([smhd])', re.I)

# Clock times: 17:30, 5pm, 5:30pm (bare "5" is rejected as ambiguous)
CLOCK_RE = re.compile(r'^(\d{1,2})(?::(\d{2}))?(am|pm)?$', re.I)

# A leading @mention to remind someone else
MENTION_RE = re.compile(r'^<@!?(\d+)>')

MULTIPLIERS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}

USAGE = (
    "usage: `@Anna remind [@user] <time> <message>`\n"
    "examples: `@Anna remind 5m check oven`, `@Anna remind 1h30m meeting`, "
    "`@Anna remind at 5pm dinner`, `@Anna remind @dave 10m your turn`\n"
    "time formats: `30s`, `5m`, `2h`, `1d`, `1h30m`, `at 17:30`, `at 5pm`"
)


def parse_time(time_str: str) -> Optional[int]:
    """
    Parse a relative time string to seconds.

    Args:
        time_str: Time string like "5m", "2h", "1d", "1h30m"

    Returns:
        Number of seconds, or None if invalid format

    Examples:
        "5m" -> 300
        "1h30m" -> 5400
        "5x" -> None
    """
    s = time_str.strip()
    if not TIME_FULL_RE.match(s):
        return None
    return sum(int(num) * MULTIPLIERS[unit.lower()] for num, unit in TIME_PART_RE.findall(s))


def parse_clock_time(token: str, now: datetime) -> Optional[int]:
    """
    Parse a clock time to seconds until its next occurrence.

    Args:
        token: Clock time like "17:30", "5pm", "5:30pm"
        now: Current time as an aware datetime in the target timezone

    Returns:
        Seconds from now until the next occurrence, or None if invalid.
        A time equal to or earlier than now means tomorrow.
    """
    m = CLOCK_RE.match(token.strip())
    if not m:
        return None

    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or '').lower()

    # Bare hour with no am/pm ("at 5") is ambiguous — reject
    if not m.group(2) and not ampm:
        return None

    if ampm:
        if not (1 <= hour <= 12):
            return None
        hour = hour % 12 + (12 if ampm == 'pm' else 0)
    elif hour > 23:
        return None
    if minute > 59:
        return None

    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return int((target - now).total_seconds())


def _local_tz():
    """The configured timezone for absolute reminder times, UTC on failure."""
    try:
        return ZoneInfo(REMINDER_TIMEZONE)
    except Exception:
        logger.warning(f"Unknown REMINDER_TIMEZONE {REMINDER_TIMEZONE!r}, falling back to UTC")
        return timezone.utc


async def remind(ctx: 'CommandContext', args: str) -> str:
    """
    Set a reminder for yourself or someone else.

    Usage: @Anna remind [@user] <time> <message>
    Examples:
        @Anna remind 5m check the oven
        @Anna remind 1h30m meeting starts
        @Anna remind at 5pm dinner time
        @Anna remind @dave 10m your turn

    Supported time formats:
        30s, 5m, 2h, 1d  - relative
        1h30m, 2d4h      - combined
        at 17:30, at 5pm - clock time (next occurrence)

    Args:
        ctx: Command context with message object
        args: Command arguments (optional mention, time, and message)

    Returns:
        Confirmation message or error
    """
    s = args.strip()
    if not s:
        return USAGE

    # Optional leading mention: remind someone else
    target_user_id = ctx.message.author.id
    target_display = "you"
    mention_match = MENTION_RE.match(s)
    if mention_match:
        target_user_id = int(mention_match.group(1))
        target_display = mention_match.group(0)
        s = s[mention_match.end():].strip()

    if not s:
        return USAGE

    first_token = s.split(maxsplit=1)[0]

    if first_token.lower() == 'at':
        # Absolute clock time: "at 5pm <message>"
        parts = s.split(maxsplit=2)
        if len(parts) < 3:
            return USAGE

        tz = _local_tz()
        now_local = datetime.now(tz)
        seconds = parse_clock_time(parts[1], now_local)
        if seconds is None:
            return f"invalid time: `{parts[1]}` — use `17:30`, `5pm`, or `5:30pm`"

        message = parts[2]
        target_time = now_local + timedelta(seconds=seconds)
        when_display = f"at {target_time.strftime('%H:%M')}"
    else:
        # Relative duration: "5m <message>"
        parts = s.split(maxsplit=1)
        if len(parts) < 2:
            return USAGE

        seconds = parse_time(parts[0])
        if seconds is None:
            return (
                f"invalid time format: `{parts[0]}`\n"
                f"use formats like: `5s`, `30m`, `2h`, `1d`, `1h30m`, `at 5pm`"
            )
        message = parts[1]
        when_display = f"in {format_duration_long(seconds)}"

    # Validate time range
    if seconds < REMINDER_MIN_TIME_SECONDS:
        return f"minimum reminder time is {REMINDER_MIN_TIME_SECONDS} seconds"
    if seconds > REMINDER_MAX_TIME_SECONDS:
        return "maximum reminder time is 1 year"

    # Calculate due time
    now = datetime.now(timezone.utc).timestamp()
    due_time = now + seconds

    reminder = ctx.reminder_manager.add_reminder(
        user_id=target_user_id,
        channel_id=ctx.message.channel.id,
        message=message,
        due_time=due_time
    )

    logger.info(
        f"Reminder created: {reminder.id} for user {target_user_id} in {seconds}s"
    )

    return f"got it, i'll remind {target_display} {when_display}: \"{message}\""
