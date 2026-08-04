"""Shuffle queue command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def shuffle(ctx: 'CommandContext', args: str) -> str:
    """
    Shuffle the current music queue.

    Usage: @Anna shuffle

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id

    count = ctx.music_manager.shuffle_queue(guild_id)

    if count == 0:
        return "queue is empty, nothing to shuffle"
    if count == 1:
        return "only one track in the queue, shuffling changed nothing"

    return f"shuffled {count} queued tracks"
