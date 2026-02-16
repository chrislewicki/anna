"""Join voice channel command."""

from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)


async def join(ctx: 'CommandContext', args: str) -> str:
    """
    Join the user's current voice channel.

    Usage: @Anna >join

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Status message
    """
    # Check if user is in a voice channel
    if not ctx.message.author.voice:
        return "you need to be in a voice channel first"

    voice_channel = ctx.message.author.voice.channel

    try:
        await ctx.music_manager.join_channel(voice_channel)
        return f"joined {voice_channel.name}"
    except Exception as e:
        logger.error(f"Failed to join voice: {e}", exc_info=True)
        return "failed to join voice channel"
