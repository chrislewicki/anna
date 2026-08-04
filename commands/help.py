"""Help command implementation."""

import inspect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def help_cmd(ctx: 'CommandContext', args: str) -> str:
    """
    Display available commands, or detailed help for one command.

    Usage: @Anna help [command]
    Examples:
        @Anna help
        @Anna help play

    Args:
        ctx: Command context
        args: Optional command name for detailed help

    Returns:
        List of available commands, or usage details for one
    """
    # Import inside function to avoid circular import
    from . import registry

    name = args.strip().lstrip('>').lower()
    if name:
        handler = registry.get(name)
        if not handler:
            return f"unknown command `{name}` — try `@Anna help`"

        doc = inspect.getdoc(handler)
        if not doc:
            return f"no help available for `{name}`"

        # Show the description and usage, drop the developer-facing sections
        for marker in ('\nArgs:', '\nReturns:'):
            doc = doc.split(marker)[0]
        return doc.strip()

    cmds = ", ".join(sorted(registry.keys()))
    return f"commands: {cmds}\ntry `@Anna help <command>` for details (e.g., `@Anna help play`)"
