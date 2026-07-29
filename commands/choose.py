"""Choose-between-options command."""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def choose(ctx: 'CommandContext', args: str) -> str:
    """
    Pick one of several options at random.

    Usage: @Anna >choose <option> | <option> [| ...]
    Examples:
        @Anna >choose pizza | tacos | sushi
        @Anna >choose red, green, blue
        @Anna >choose heads tails

    Options split on `|` if present, then commas, then spaces.

    Args:
        ctx: Command context
        args: Options to choose between

    Returns:
        The chosen option
    """
    if '|' in args:
        options = args.split('|')
    elif ',' in args:
        options = args.split(',')
    else:
        options = args.split()

    options = [o.strip() for o in options if o.strip()]
    if len(options) < 2:
        return "give me at least two options, e.g. `>choose pizza | tacos`"

    return f"i choose: **{random.choice(options)}**"
