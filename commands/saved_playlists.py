"""Saved playlist commands: save, load, list, and delete the queue by name."""

from typing import TYPE_CHECKING
from playlist_resolver import PlaylistTrack
from .play import _ensure_voice
import steely_dan

if TYPE_CHECKING:
    from message_handler import CommandContext

MAX_NAME_LENGTH = 50


async def saveq(ctx: 'CommandContext', args: str) -> str:
    """
    Save the current queue (including the playing track) as a named playlist.

    Usage: @Anna saveq <name>
    Example: @Anna saveq friday bangers

    Args:
        ctx: Command context
        args: Playlist name

    Returns:
        Status message
    """
    if ctx.playlist_store is None:
        return "saved playlists are unavailable"

    name = args.strip()
    if not name:
        return "usage: `@Anna saveq <name>`"
    if len(name) > MAX_NAME_LENGTH:
        return f"name too long (max {MAX_NAME_LENGTH} characters)"

    guild_id = ctx.message.guild.id
    music_manager = ctx.music_manager

    tracks = []
    now_playing = music_manager.now_playing.get(guild_id)
    if now_playing:
        tracks.append({"url": now_playing.url, "title": now_playing.title})
    for track in music_manager.queues.get(guild_id) or []:
        tracks.append({"url": track.url, "title": track.title})

    if not tracks:
        return "nothing playing and queue is empty — nothing to save"

    ctx.playlist_store.save_playlist(guild_id, name, tracks)
    return f"saved **{name}** ({len(tracks)} tracks)"


async def loadq(ctx: 'CommandContext', args: str) -> str:
    """
    Load a saved playlist into the queue.

    Usage: @Anna loadq <name>
    Example: @Anna loadq friday bangers

    Args:
        ctx: Command context
        args: Playlist name

    Returns:
        Status message
    """
    if ctx.playlist_store is None:
        return "saved playlists are unavailable"

    name = args.strip()
    if not name:
        return "usage: `@Anna loadq <name>` (see `@Anna playlists`)"

    guild_id = ctx.message.guild.id
    playlist = ctx.playlist_store.get_playlist(guild_id, name)
    if playlist is None:
        return f"no saved playlist named **{name}** — see `@Anna playlists`"

    error = await _ensure_voice(ctx)
    if error:
        return error

    tracks = [PlaylistTrack(query=t["url"], title=t["title"]) for t in playlist["tracks"]]

    # Playlists saved before the ban can still be carrying contraband
    tracks, dropped = steely_dan.purge(tracks)
    if not tracks:
        return f"**{playlist['name']}** is wall-to-wall Steely Dan. queued nothing. {steely_dan.refusal()}"

    success, message = await ctx.music_manager.add_playlist_to_queue(
        guild_id,
        tracks,
        ctx.message.author.id,
        channel_id=ctx.message.channel.id
    )

    if not success:
        return message

    return f"queued {len(tracks)} tracks from **{playlist['name']}**{steely_dan.playlist_note(dropped)}"


async def playlists(ctx: 'CommandContext', args: str) -> str:
    """
    List this server's saved playlists.

    Usage: @Anna playlists

    Args:
        ctx: Command context
        args: Unused

    Returns:
        List of saved playlists
    """
    if ctx.playlist_store is None:
        return "saved playlists are unavailable"

    saved = ctx.playlist_store.list_playlists(ctx.message.guild.id)
    if not saved:
        return "no saved playlists — save the queue with `@Anna saveq <name>`"

    lines = ["**saved playlists:**"]
    for playlist in saved:
        lines.append(f"- {playlist['name']} ({len(playlist['tracks'])} tracks)")
    lines.append("load one with `@Anna loadq <name>`")
    return "\n".join(lines)


async def delq(ctx: 'CommandContext', args: str) -> str:
    """
    Delete a saved playlist.

    Usage: @Anna delq <name>

    Args:
        ctx: Command context
        args: Playlist name

    Returns:
        Status message
    """
    if ctx.playlist_store is None:
        return "saved playlists are unavailable"

    name = args.strip()
    if not name:
        return "usage: `@Anna delq <name>`"

    if ctx.playlist_store.delete_playlist(ctx.message.guild.id, name):
        return f"deleted playlist **{name}**"
    return f"no saved playlist named **{name}**"
