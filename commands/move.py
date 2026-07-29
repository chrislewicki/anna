"""Move a track within the queue."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def move(ctx: 'CommandContext', args: str) -> str:
    """
    Move a track from one queue position to another.

    Usage: @Anna >move <from> <to>
    Example: @Anna >move 5 1

    Positions match the numbers shown by >queue.

    Args:
        ctx: Command context
        args: Two 1-based queue positions

    Returns:
        Status message
    """
    parts = args.split()
    if len(parts) != 2:
        return "usage: `>move <from> <to>` (see positions with `>queue`)"

    try:
        from_pos, to_pos = int(parts[0]), int(parts[1])
    except ValueError:
        return "usage: `>move <from> <to>` (see positions with `>queue`)"

    track = ctx.music_manager.move_in_queue(ctx.message.guild.id, from_pos, to_pos)
    if track is None:
        return "invalid positions — check `>queue`"

    return f"moved to position {to_pos}: {track.title}"
