"""Now playing command."""

import time
from typing import TYPE_CHECKING
from utils import format_track_time

if TYPE_CHECKING:
    from message_handler import CommandContext


async def nowplaying(ctx: 'CommandContext', args: str) -> str:
    """
    Show the currently playing track.

    Usage: @Anna nowplaying (or @Anna np)

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Current track info with playback progress
    """
    guild_id = ctx.message.guild.id
    music_manager = ctx.music_manager

    now_playing = music_manager.now_playing.get(guild_id)

    if not now_playing:
        return "nothing is currently playing"

    lines = [f"**now playing:** {now_playing.title}"]

    if now_playing.started_at:
        elapsed = int(time.time() - now_playing.started_at)
        if now_playing.duration:
            elapsed = min(elapsed, now_playing.duration)
            lines.append(
                f"**progress:** {format_track_time(elapsed)} / {format_track_time(now_playing.duration)}"
            )
        else:
            lines.append(f"**elapsed:** {format_track_time(elapsed)}")
    elif now_playing.duration:
        lines.append(f"**duration:** {format_track_time(now_playing.duration)}")

    lines.append(f"**requested by:** <@{now_playing.requester_id}>")

    return "\n".join(lines)
