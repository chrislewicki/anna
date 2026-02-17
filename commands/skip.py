"""Skip track command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def skip(ctx: 'CommandContext', args: str) -> str:
    """
    Skip the currently playing track.

    Usage: @Anna >skip

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id
    music_manager = ctx.music_manager

    voice_client = music_manager.get_voice_client(guild_id)
    if not voice_client:
        return "not in a voice channel"

    # Check if something is playing
    if not voice_client.is_playing() and not voice_client.is_paused():
        return "nothing is playing"

    # Get current track info for response
    now_playing = music_manager.now_playing.get(guild_id)
    track_name = now_playing.title if now_playing else "current track"

    # Stop current track (will trigger callback to play next)
    voice_client.stop()

    # Check if there's a next track
    queue_items = music_manager.queues.get(guild_id)
    if queue_items and len(queue_items) > 0:
        return f"skipped: {track_name}"
    else:
        return f"skipped: {track_name} (queue is now empty)"
