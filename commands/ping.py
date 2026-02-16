"""Ping command implementation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def ping(ctx: 'CommandContext', args: str) -> str:
    """
    Simple ping command to test bot responsiveness.

    Args:
        ctx: Command context
        args: Command arguments (unused)

    Returns:
        "pong" response
    """
    return "pong"
