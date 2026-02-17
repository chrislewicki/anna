"""Stop playback command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def stop(ctx: 'CommandContext', args: str) -> str:
    """Stop current playback."""
    guild_id = ctx.message.guild.id
    success = ctx.music_manager.stop(guild_id)
    return "stopped playback" if success else "nothing is playing"
