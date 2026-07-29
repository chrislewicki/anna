"""Magic 8-ball command."""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext

RESPONSES = [
    "it is certain",
    "it is decidedly so",
    "without a doubt",
    "yes, definitely",
    "you may rely on it",
    "as i see it, yes",
    "most likely",
    "outlook good",
    "yes",
    "signs point to yes",
    "reply hazy, try again",
    "ask again later",
    "better not tell you now",
    "cannot predict now",
    "concentrate and ask again",
    "don't count on it",
    "my reply is no",
    "my sources say no",
    "outlook not so good",
    "very doubtful",
]


async def eightball(ctx: 'CommandContext', args: str) -> str:
    """
    Consult the magic 8-ball.

    Usage: @Anna >8ball <question>
    Example: @Anna >8ball will it rain tomorrow?

    Args:
        ctx: Command context
        args: The question

    Returns:
        The 8-ball's wisdom
    """
    if not args.strip():
        return "ask me a question, e.g. `>8ball will it rain tomorrow?`"

    return f"🎱 {random.choice(RESPONSES)}"
