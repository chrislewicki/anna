"""Clear queue command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def clear(ctx: 'CommandContext', args: str) -> str:
    """
    Clear the music queue.

    Usage: @Anna >clear

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id
    music_manager = ctx.music_manager

    queue_items = music_manager.queues.get(guild_id)

    if not queue_items or len(queue_items) == 0:
        return "queue is already empty"

    count = len(queue_items)
    queue_items.clear()

    return f"cleared {count} track(s) from queue"
