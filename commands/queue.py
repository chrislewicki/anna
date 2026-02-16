"""Queue viewing command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def queue(ctx: 'CommandContext', args: str) -> str:
    """
    View the current music queue.

    Usage: @Anna >queue

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Formatted queue display
    """
    guild_id = ctx.message.guild.id
    music_manager = ctx.music_manager

    # Get currently playing track
    now_playing = music_manager.now_playing.get(guild_id)

    # Get queue
    queue_items = music_manager.queues.get(guild_id)

    # Build response
    lines = []

    if now_playing:
        lines.append(f"**now playing:** {now_playing.title}")
    else:
        lines.append("**now playing:** nothing")

    if queue_items and len(queue_items) > 0:
        lines.append(f"\n**up next:** ({len(queue_items)} track(s))")
        for i, track in enumerate(queue_items, 1):
            # Limit display to first 10 tracks
            if i > 10:
                remaining = len(queue_items) - 10
                lines.append(f"...and {remaining} more")
                break
            lines.append(f"{i}. {track.title}")
    else:
        lines.append("\n**queue is empty**")

    return "\n".join(lines)
