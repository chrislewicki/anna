"""Leave voice channel command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def leave(ctx: 'CommandContext', args: str) -> str:
    """
    Leave the voice channel.

    Usage: @Anna >leave

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id
    success = await ctx.music_manager.leave_channel(guild_id)

    if success:
        return "left voice channel"
    else:
        return "not in a voice channel"
