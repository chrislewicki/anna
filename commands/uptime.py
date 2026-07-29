"""Uptime command implementation."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from state import START_TS
from utils import format_duration_long

if TYPE_CHECKING:
    from message_handler import CommandContext


async def uptime(ctx: 'CommandContext', args: str) -> str:
    """
    Display bot uptime since startup.

    Usage: @Anna uptime

    Args:
        ctx: Command context
        args: Command arguments (unused)

    Returns:
        Human-readable uptime
    """
    delta = datetime.now(timezone.utc) - START_TS
    return f"Uptime: {format_duration_long(int(delta.total_seconds()))}"
