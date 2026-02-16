"""Pause playback command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def pause(ctx: 'CommandContext', args: str) -> str:
    """Pause current playback."""
    guild_id = ctx.message.guild.id
    success = ctx.music_manager.pause(guild_id)
    return "paused" if success else "nothing is playing"
