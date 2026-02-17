"""Resume playback command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def resume(ctx: 'CommandContext', args: str) -> str:
    """Resume paused playback."""
    guild_id = ctx.message.guild.id
    success = ctx.music_manager.resume(guild_id)
    return "resumed" if success else "nothing is paused"
