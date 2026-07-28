"""Play music command."""

from typing import TYPE_CHECKING
import asyncio
import logging
from streaming_resolver import is_streaming_url, resolve_streaming_url
from playlist_resolver import is_playlist_url, resolve_playlist

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)


async def play(ctx: 'CommandContext', args: str) -> str:
    """
    Play audio from a URL, playlist URL, or search query.

    Usage: @Anna >play <url or search terms>
    Examples:
        @Anna >play https://www.youtube.com/watch?v=dQw4w9WgXcQ
        @Anna >play https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
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
    is_url = query.startswith(('http://', 'https://', 'www.')) or '/' in query

    # Playlist links (Spotify, Apple Music, YouTube/YT Music) queue every track
    if is_url and is_playlist_url(query):
        return await _play_playlist(ctx, query)

    # Resolve streaming service links (Spotify, Apple Music, Tidal, etc.)
    if is_url and is_streaming_url(query):
        try:
            query = resolve_streaming_url(query)
            logger.info(f"Resolved streaming URL to: {query}")
            is_url = query.startswith(('http://', 'https://'))
        except RuntimeError as e:
            return str(e)

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


async def _play_playlist(ctx: 'CommandContext', url: str) -> str:
    """Resolve a playlist URL and queue all of its tracks in order."""
    guild_id = ctx.message.guild.id

    # Join the user's voice channel if not already connected
    if not ctx.music_manager.get_voice_client(guild_id):
        if not ctx.message.author.voice:
            return "i'm not in a voice channel. use `>join` first or join a voice channel yourself"

        try:
            await ctx.music_manager.join_channel(ctx.message.author.voice.channel)
        except Exception as e:
            logger.error(f"Auto-join failed: {e}")
            return "failed to join your voice channel"

    # Resolution hits the network and can take a few seconds for big
    # playlists, so run it off the event loop
    try:
        playlist = await asyncio.to_thread(resolve_playlist, url)
    except RuntimeError as e:
        return str(e)

    success, message = await ctx.music_manager.add_playlist_to_queue(
        guild_id,
        playlist.tracks,
        ctx.message.author.id
    )

    if not success:
        return message

    return f"queued {len(playlist.tracks)} tracks from **{playlist.name}**"
