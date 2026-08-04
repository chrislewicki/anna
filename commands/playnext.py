"""Play-next command (front-queue a track)."""

from typing import TYPE_CHECKING
import logging
from playlist_resolver import is_playlist_url
from .play import _ensure_voice, _resolve_single_query

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)


async def playnext(ctx: 'CommandContext', args: str) -> str:
    """
    Queue a track to play next, ahead of everything else in the queue.

    Usage: @Anna playnext <url or search terms>
    Examples:
        @Anna playnext https://www.youtube.com/watch?v=dQw4w9WgXcQ
        @Anna playnext aespa whiplash

    Args:
        ctx: Command context
        args: URL or search terms

    Returns:
        Status message
    """
    if not args.strip():
        return "usage: `@Anna playnext <url or search terms>`"

    query = args.strip()

    if is_playlist_url(query):
        return "playlists can't be front-queued — use `@Anna play` for those"

    try:
        query = _resolve_single_query(query)
    except RuntimeError as e:
        return str(e)

    error = await _ensure_voice(ctx)
    if error:
        return error

    success, message = await ctx.music_manager.add_to_queue(
        ctx.message.guild.id,
        query,
        ctx.message.author.id,
        channel_id=ctx.message.channel.id,
        play_next=True
    )

    return message
