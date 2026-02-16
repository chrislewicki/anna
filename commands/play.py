"""Play music command."""

from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)


async def play(ctx: 'CommandContext', args: str) -> str:
    """
    Play audio from a URL or search query.

    Usage: @Anna >play <url or search terms>
    Examples:
        @Anna >play https://www.youtube.com/watch?v=dQw4w9WgXcQ
        @Anna >play aespa whiplash
        @Anna >play lofi hip hop beats

    Args:
        ctx: Command context
        args: URL or search terms

    Returns:
        Status message
    """
    if not args.strip():
        return "usage: `>play <url or search terms>`"

    query = args.strip()

    # Detect if it's a URL or search terms
    # If it doesn't look like a URL, prepend ytsearch1: to search YouTube for first result
    is_url = query.startswith(('http://', 'https://', 'www.')) or '/' in query

    if not is_url:
        # Search YouTube for first result
        query = f"ytsearch1:{query}"
        logger.info(f"Searching YouTube for: {args.strip()}")

    # Check if bot is in voice channel
    guild_id = ctx.message.guild.id
    voice_client = ctx.music_manager.get_voice_client(guild_id)

    # If not in voice, try to join user's channel
    if not voice_client:
        if not ctx.message.author.voice:
            return "i'm not in a voice channel. use `>join` first or join a voice channel yourself"

        try:
            await ctx.music_manager.join_channel(ctx.message.author.voice.channel)
        except Exception as e:
            logger.error(f"Auto-join failed: {e}")
            return "failed to join your voice channel"

    # Add to queue (will start playing if nothing is playing)
    success, message = await ctx.music_manager.add_to_queue(
        guild_id,
        query,
        ctx.message.author.id
    )

    return message
