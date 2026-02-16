"""Reminder command implementation."""

import re
import logging
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from config import REMINDER_MIN_TIME_SECONDS, REMINDER_MAX_TIME_SECONDS

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)

# Regex pattern for time parsing: <number><unit>
# Examples: 5s, 30m, 2h, 1d
TIME_REGEX = re.compile(r'^(\d+)([smhd])$', re.I)


def parse_time(time_str: str) -> Optional[int]:
    """
    Parse relative time string to seconds.

    Args:
        time_str: Time string like "5m", "2h", "1d"

    Returns:
        Number of seconds, or None if invalid format

    Examples:
        "5m" -> 300
        "2h" -> 7200
        "1d" -> 86400
        "5x" -> None
    """
    m = TIME_REGEX.match(time_str.strip())
    if not m:
        return None

    num = int(m.group(1))
    unit = m.group(2).lower()

    # Convert to seconds
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }

    return num * multipliers.get(unit, 0)


def format_duration(seconds: int) -> str:
    """
    Format seconds into human-readable duration.

    Args:
        seconds: Number of seconds

    Returns:
        Formatted string like "5m", "2h", "1d"
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"


async def remind(ctx: 'CommandContext', args: str) -> str:
    """
    Set a reminder.

    Usage: @Anna >remind <time> <message>
    Examples:
        @Anna >remind 5m check the oven
        @Anna >remind 2h meeting starts
        @Anna >remind 1d dentist appointment

    Supported time formats:
        5s, 30s  - seconds
        5m, 30m  - minutes
        2h, 12h  - hours
        1d, 7d   - days

    Args:
        ctx: Command context with message object
        args: Command arguments (time and message)

    Returns:
        Confirmation message or error
    """
    # Parse args: first token is time, rest is message
    parts = args.strip().split(maxsplit=1)

    if len(parts) < 2:
        return (
            "usage: `>remind <time> <message>`\n"
            "examples: `>remind 5m check oven`, `>remind 2h meeting`\n"
            "time formats: `5s`, `30m`, `2h`, `1d`"
        )

    time_str, message = parts
    seconds = parse_time(time_str)

    # Validate time format
    if seconds is None:
        return (
            f"invalid time format: `{time_str}`\n"
            f"use formats like: `5s`, `30m`, `2h`, `1d`"
        )

    # Validate time range
    if seconds < REMINDER_MIN_TIME_SECONDS:
        return f"minimum reminder time is {REMINDER_MIN_TIME_SECONDS} seconds"

    if seconds > REMINDER_MAX_TIME_SECONDS:
        return "maximum reminder time is 1 year"

    # Calculate due time
    now = datetime.now(timezone.utc).timestamp()
    due_time = now + seconds

    # Create reminder using context manager
    reminder = ctx.reminder_manager.add_reminder(
        user_id=ctx.message.author.id,
        channel_id=ctx.message.channel.id,
        message=message,
        due_time=due_time
    )

    # Format response
    time_display = format_duration(seconds)
    logger.info(
        f"Reminder created: {reminder.id} for user {ctx.message.author.id} "
        f"in {seconds}s ({time_display})"
    )

    return f"got it, i'll remind you in {time_display}: \"{message}\""
