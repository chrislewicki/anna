"""Play music command."""

from typing import TYPE_CHECKING, Optional
import asyncio
import logging
from streaming_resolver import is_streaming_url, resolve_streaming_url
from playlist_resolver import is_playlist_url, resolve_playlist

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)


async def _ensure_voice(ctx: 'CommandContext') -> Optional[str]:
    """
    Make sure the bot is connected to voice, joining the user's channel if needed.

    Returns:
        An error message string, or None if connected
    """
    guild_id = ctx.message.guild.id
    if ctx.music_manager.get_voice_client(guild_id):
        return None

    if not ctx.message.author.voice:
        return "i'm not in a voice channel. use `@Anna join` first or join a voice channel yourself"

    try:
        await ctx.music_manager.join_channel(ctx.message.author.voice.channel)
        return None
    except Exception as e:
        logger.error(f"Auto-join failed: {e}")
        return "failed to join your voice channel"


def _resolve_single_query(query: str) -> str:
    """
    Turn user input into a yt-dlp input: a URL or a ytsearch1: search string.

    Resolves single-track streaming service links (Spotify, Apple Music, etc.)
    via odesli.

    Raises:
        RuntimeError: If a streaming link can't be resolved
    """
    is_url = query.startswith(('http://', 'https://', 'www.')) or '/' in query

    if is_url and is_streaming_url(query):
        query = resolve_streaming_url(query)
        logger.info(f"Resolved streaming URL to: {query}")
        is_url = query.startswith(('http://', 'https://'))

    if not is_url:
        logger.info(f"Searching YouTube for: {query}")
        query = f"ytsearch1:{query}"

    return query


async def play(ctx: 'CommandContext', args: str) -> str:
    """
    Play audio from a URL, playlist URL, or search query.

    Usage: @Anna play <url or search terms>
    Examples:
        @Anna play https://www.youtube.com/watch?v=dQw4w9WgXcQ
        @Anna play https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
        @Anna play aespa whiplash
        @Anna play lofi hip hop beats

    Args:
        ctx: Command context
        args: URL or search terms

    Returns:
        Status message
    """
    if not args.strip():
        return "usage: `@Anna play <url or search terms>`"

    query = args.strip()
    is_url = query.startswith(('http://', 'https://', 'www.')) or '/' in query

    # Playlist links (Spotify, Apple Music, YouTube/YT Music) queue every track
    if is_url and is_playlist_url(query):
        return await _play_playlist(ctx, query)

    try:
        query = _resolve_single_query(query)
    except RuntimeError as e:
        return str(e)

    error = await _ensure_voice(ctx)
    if error:
        return error

    # Add to queue (will start playing if nothing is playing)
    success, message = await ctx.music_manager.add_to_queue(
        ctx.message.guild.id,
        query,
        ctx.message.author.id,
        channel_id=ctx.message.channel.id
    )

    return message


async def _play_playlist(ctx: 'CommandContext', url: str) -> str:
    """Resolve a playlist URL and queue all of its tracks in order."""
    error = await _ensure_voice(ctx)
    if error:
        return error

    # Resolution hits the network and can take a few seconds for big
    # playlists, so run it off the event loop
    try:
        playlist = await asyncio.to_thread(resolve_playlist, url)
    except RuntimeError as e:
        return str(e)

    success, message = await ctx.music_manager.add_playlist_to_queue(
        ctx.message.guild.id,
        playlist.tracks,
        ctx.message.author.id,
        channel_id=ctx.message.channel.id
    )

    if not success:
        return message

    return f"queued {len(playlist.tracks)} tracks from **{playlist.name}**"
