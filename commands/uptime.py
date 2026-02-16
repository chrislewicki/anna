"""Uptime command implementation."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from state import START_TS

if TYPE_CHECKING:
    from message_handler import CommandContext


async def uptime(ctx: 'CommandContext', args: str) -> str:
    """
    Display bot uptime since startup.

    Args:
        ctx: Command context
        args: Command arguments (unused)

    Returns:
        Uptime in seconds
    """
    delta = datetime.now(timezone.utc) - START_TS
    secs = int(delta.total_seconds())
    return f"Uptime: {secs}s"
