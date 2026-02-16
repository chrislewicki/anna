"""Help command implementation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def help_cmd(ctx: 'CommandContext', args: str) -> str:
    """
    Display available commands.

    Args:
        ctx: Command context
        args: Command arguments (unused)

    Returns:
        List of available commands
    """
    # Import inside function to avoid circular import
    from . import registry
    cmds = ", ".join(sorted(registry.keys()))
    return f"commands: {cmds} - prefix with `>` (e.g., `>ping`)"
