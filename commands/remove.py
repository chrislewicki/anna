"""Remove a track from the queue."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def remove(ctx: 'CommandContext', args: str) -> str:
    """
    Remove a track from the queue by its position.

    Usage: @Anna remove <position>
    Example: @Anna remove 3

    Positions match the numbers shown by the queue command.

    Args:
        ctx: Command context
        args: 1-based queue position

    Returns:
        Status message
    """
    try:
        position = int(args.strip())
    except ValueError:
        return "usage: `@Anna remove <position>` (see positions with `@Anna queue`)"

    track = ctx.music_manager.remove_from_queue(ctx.message.guild.id, position)
    if track is None:
        return f"no track at position {position} — check `@Anna queue`"

    return f"removed: {track.title}"
