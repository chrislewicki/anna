"""Now playing command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def nowplaying(ctx: 'CommandContext', args: str) -> str:
    """
    Show the currently playing track.

    Usage: @Anna >nowplaying (or >np)

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Current track info
    """
    guild_id = ctx.message.guild.id
    music_manager = ctx.music_manager

    now_playing = music_manager.now_playing.get(guild_id)

    if not now_playing:
        return "nothing is currently playing"

    lines = [f"**now playing:** {now_playing.title}"]

    if now_playing.duration:
        minutes = now_playing.duration // 60
        seconds = now_playing.duration % 60
        lines.append(f"**duration:** {minutes}:{seconds:02d}")

    lines.append(f"**requested by:** <@{now_playing.requester_id}>")

    return "\n".join(lines)
