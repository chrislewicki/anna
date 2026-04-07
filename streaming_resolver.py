"""Streaming service link resolution via odesli.co API."""

from urllib.parse import urlparse
import requests
import logging

logger = logging.getLogger(__name__)

ODESLI_API_URL = "https://api.song.link/v1-alpha.1/links"

STREAMING_DOMAINS = {
    'open.spotify.com', 'spotify.link', 'spotify.com',
    'music.apple.com', 'itunes.apple.com',
    'tidal.com',
    'deezer.com', 'deezer.page.link',
    'music.amazon.com',
    'music.youtube.com',
    'soundcloud.com',
    'pandora.com',
}


def is_streaming_url(url: str) -> bool:
    """Return True if URL is from a known streaming service (not plain YouTube)."""
    try:
        netloc = urlparse(url).netloc.lower().lstrip('www.')
        return any(netloc == domain or netloc.endswith('.' + domain)
                   for domain in STREAMING_DOMAINS)
    except Exception:
        return False


def resolve_streaming_url(url: str) -> str:
    """
    Resolve a streaming service URL to a playable YouTube URL or search query.

    Calls the odesli.co API to find cross-platform links and metadata.
    Prefers a direct YouTube URL; falls back to "ytsearch1:Artist - Title".

    Args:
        url: A streaming service URL (Spotify, Apple Music, etc.)

    Returns:
        A YouTube URL string, or a ytsearch1: prefixed search string.

    Raises:
        RuntimeError: If the API request fails or the track cannot be found.
    """
    logger.info(f"Resolving streaming URL via odesli: {url}")

    try:
        resp = requests.get(
            ODESLI_API_URL,
            params={"url": url, "userCountry": "US"},
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("couldn't resolve streaming link: request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"couldn't resolve streaming link: {e}")

    if resp.status_code == 404:
        raise RuntimeError("couldn't find that track on any streaming platform")
    if resp.status_code != 200:
        raise RuntimeError(f"couldn't resolve streaming link (odesli returned {resp.status_code})")

    try:
        data = resp.json()
    except Exception:
        raise RuntimeError("couldn't resolve streaming link: invalid response")

    logger.debug(f"Odesli response keys: {list(data.keys())}")
    logger.debug(f"Odesli linksByPlatform keys: {list(data.get('linksByPlatform', {}).keys())}")
    logger.debug(f"Odesli entityUniqueId: {data.get('entityUniqueId')}")

    # Try direct YouTube URL first
    links = data.get('linksByPlatform', {})
    youtube_link = links.get('youtube', {}).get('url')
    if youtube_link:
        logger.info(f"Resolved to YouTube URL: {youtube_link}")
        return youtube_link

    # Fall back to YouTube Music link
    yt_music_link = links.get('youtubeMusic', {}).get('url')
    if yt_music_link:
        logger.info(f"Resolved to YouTube Music URL: {yt_music_link}")
        return yt_music_link

    # Fall back to search by title + artist
    entities = data.get('entitiesByUniqueId', {})
    primary_id = data.get('entityUniqueId')
    logger.debug(f"Odesli entities keys: {list(entities.keys())}, primary_id: {primary_id}")

    entity = entities.get(primary_id, next(iter(entities.values()), {}))
    logger.debug(f"Odesli entity: {entity}")

    title = entity.get('title', '')
    artist = entity.get('artistName', '')

    if title:
        search_query = f"{artist} {title}".strip() if artist else title
        logger.info(f"No YouTube link found, falling back to search: {search_query}")
        return f"ytsearch1:{search_query}"

    raise RuntimeError("couldn't resolve streaming link: no track info or YouTube link found")
