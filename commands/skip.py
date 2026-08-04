"""Skip track command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def skip(ctx: 'CommandContext', args: str) -> str:
    """
    Skip the currently playing track.

    Usage: @Anna skip

    Skipping always moves to the next track, even when `@Anna loop track` is on.

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id
    music_manager = ctx.music_manager

    if not music_manager.get_voice_client(guild_id):
        return "not in a voice channel"

    title = music_manager.skip(guild_id)
    if title is None:
        return "nothing is playing"

    queue_items = music_manager.queues.get(guild_id)
    if queue_items and len(queue_items) > 0:
        return f"skipped: {title}"
    else:
        return f"skipped: {title} (queue is now empty)"
