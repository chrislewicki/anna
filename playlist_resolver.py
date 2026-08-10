"""Playlist link resolution for Spotify, Apple Music, and YouTube/YouTube Music."""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse, parse_qs

import requests
import yt_dlp

from utils import youtube_search_query

logger = logging.getLogger(__name__)

REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
    ),
}

YDL_FLAT_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'extract_flat': 'in_playlist',
}


@dataclass
class PlaylistTrack:
    """A single track resolved from a playlist."""
    query: str  # yt-dlp input: a URL or a "ytsearch1:" search string
    title: str  # display title for the queue


@dataclass
class ResolvedPlaylist:
    """An ordered list of tracks resolved from a playlist URL."""
    name: str
    tracks: List[PlaylistTrack] = field(default_factory=list)


def _netloc(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith('www.') else netloc


def is_playlist_url(url: str) -> bool:
    """Return True if URL points to a playlist/album on a supported service."""
    try:
        parsed = urlparse(url)
        host = _netloc(url)
        path = parsed.path
        query = parse_qs(parsed.query)
    except Exception:
        return False

    if host in ('open.spotify.com', 'spotify.com'):
        return re.search(r'/(playlist|album)/[A-Za-z0-9]+', path) is not None

    if host in ('music.apple.com', 'itunes.apple.com'):
        if '/playlist/' in path:
            return True
        # Album link without ?i= (with ?i= it's a single song on that album)
        return '/album/' in path and 'i' not in query

    if host in ('youtube.com', 'music.youtube.com', 'm.youtube.com'):
        return path == '/playlist' and 'list' in query

    return False


def resolve_playlist(url: str) -> ResolvedPlaylist:
    """
    Resolve a playlist URL to an ordered list of playable tracks.

    Spotify and Apple Music tracks become "ytsearch1:Artist Title" queries;
    YouTube/YouTube Music entries keep their direct video URLs.

    Raises:
        RuntimeError: With a user-friendly message if resolution fails.
    """
    host = _netloc(url)

    if host in ('open.spotify.com', 'spotify.com'):
        playlist = _resolve_spotify(url)
    elif host in ('music.apple.com', 'itunes.apple.com'):
        playlist = _resolve_apple_music(url)
    else:
        playlist = _resolve_youtube(url)

    if not playlist.tracks:
        raise RuntimeError("couldn't find any tracks in that playlist")

    logger.info(f"Resolved playlist '{playlist.name}': {len(playlist.tracks)} tracks")
    return playlist


def _fetch_page(url: str) -> str:
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    except requests.exceptions.Timeout:
        raise RuntimeError("couldn't fetch that playlist: request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"couldn't fetch that playlist: {e}")

    if resp.status_code != 200:
        raise RuntimeError(f"couldn't fetch that playlist (got HTTP {resp.status_code})")
    # Apple Music omits the charset header and requests then assumes
    # ISO-8859-1, garbling curly quotes etc. — both services serve UTF-8
    return resp.content.decode('utf-8', errors='replace')


def _search_track(title: str, artist: str) -> PlaylistTrack:
    query = f"{artist} {title}".strip() if artist else title
    display = f"{title} — {artist}" if artist else title
    return PlaylistTrack(query=youtube_search_query(query), title=display)


def _resolve_spotify(url: str) -> ResolvedPlaylist:
    """Resolve a Spotify playlist/album via its public embed page JSON."""
    m = re.search(r'/(playlist|album)/([A-Za-z0-9]+)', urlparse(url).path)
    if not m:
        raise RuntimeError("that doesn't look like a spotify playlist or album link")
    kind, spotify_id = m.groups()

    html = _fetch_page(f"https://open.spotify.com/embed/{kind}/{spotify_id}")

    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    if not m:
        raise RuntimeError("couldn't read the spotify playlist page (layout may have changed)")

    try:
        data = json.loads(m.group(1))
        entity = data['props']['pageProps']['state']['data']['entity']
        track_list = entity.get('trackList', [])
    except (json.JSONDecodeError, KeyError, TypeError):
        raise RuntimeError("couldn't read the spotify playlist page (layout may have changed)")

    tracks = []
    for item in track_list:
        title = item.get('title')
        if not title:
            continue
        tracks.append(_search_track(title, item.get('subtitle', '')))

    return ResolvedPlaylist(name=entity.get('name') or 'Spotify playlist', tracks=tracks)


def _resolve_apple_music(url: str) -> ResolvedPlaylist:
    """Resolve an Apple Music playlist/album from its embedded page JSON."""
    html = _fetch_page(url)

    # Primary: the serialized-server-data blob. It's present on all page
    # types (user playlists have no ld+json at all) and carries ordered
    # title + artist per track.
    playlist = _parse_apple_server_data(html)
    if playlist is not None:
        return playlist

    return _parse_apple_ldjson(html)


def _parse_apple_server_data(html: str):
    """Parse tracks from Apple's serialized-server-data JSON, or None if the shape doesn't match."""
    m = re.search(r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None

    try:
        page = json.loads(m.group(1))['data'][0]['data']
        sections = page['sections']
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None

    name = 'Apple Music playlist'
    tracks = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        items = section.get('items') or []
        kind = section.get('itemKind')
        if kind == 'containerDetailHeaderLockup' and items:
            name = items[0].get('title') or name
        elif kind == 'trackLockup':
            for item in items:
                title = item.get('title')
                if not title:
                    continue
                tracks.append(_search_track(title, item.get('artistName', '')))

    if not tracks:
        return None
    return ResolvedPlaylist(name=name, tracks=tracks)


def _parse_apple_ldjson(html: str) -> ResolvedPlaylist:
    """Fallback: parse tracks from the page's ld+json (absent on user playlists)."""
    m = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("couldn't read the apple music page (layout may have changed)")

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        raise RuntimeError("couldn't read the apple music page (layout may have changed)")

    # Playlists use "track", albums use "tracks"
    raw_tracks = data.get('track') or data.get('tracks') or []
    name = data.get('name') or 'Apple Music playlist'

    # Albums carry a single artist at the top level
    album_artist = ''
    by_artist = data.get('byArtist')
    if isinstance(by_artist, list) and by_artist:
        by_artist = by_artist[0]
    if isinstance(by_artist, dict):
        album_artist = by_artist.get('name', '')

    # Playlist pages don't put artists in ld+json; build a title -> artist
    # map from the serialized-server-data blob instead.
    artist_by_title = {} if album_artist else _apple_artist_map(html)

    tracks = []
    for item in raw_tracks:
        title = item.get('name')
        if not title:
            continue
        artist = album_artist or artist_by_title.get(title, '')
        tracks.append(_search_track(title, artist))

    return ResolvedPlaylist(name=name, tracks=tracks)


def _apple_artist_map(html: str) -> dict:
    """Extract a {track title: artist name} map from Apple's server-data JSON."""
    m = re.search(r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}

    result = {}

    def walk(obj, depth=0):
        if depth > 15:
            return
        if isinstance(obj, dict):
            title = obj.get('title')
            artist = obj.get('artistName')
            if isinstance(title, str) and isinstance(artist, str):
                result.setdefault(title, artist)
                return
            for value in obj.values():
                walk(value, depth + 1)
        elif isinstance(obj, list):
            for value in obj:
                walk(value, depth + 1)

    walk(data)
    return result


def _resolve_youtube(url: str) -> ResolvedPlaylist:
    """Resolve a YouTube / YouTube Music playlist via yt-dlp flat extraction."""
    try:
        with yt_dlp.YoutubeDL(YDL_FLAT_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise RuntimeError(f"couldn't read that youtube playlist: {e}")

    entries = info.get('entries') or []
    tracks = []
    for entry in entries:
        if not entry:
            continue
        title = entry.get('title') or 'Unknown'
        video_url = entry.get('url')
        if not video_url and entry.get('id'):
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
        if not video_url:
            continue
        tracks.append(PlaylistTrack(query=video_url, title=title))

    return ResolvedPlaylist(name=info.get('title') or 'YouTube playlist', tracks=tracks)
