"""Tests for playlist URL detection and page parsing (no network)."""

import json

import pytest

import playlist_resolver
from playlist_resolver import (
    is_playlist_url,
    resolve_playlist,
    _parse_apple_server_data,
    _resolve_spotify,
    _resolve_youtube,
)
from conftest import FakeYDL


# --- URL detection ---

@pytest.mark.parametrize("url,expected", [
    ("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M", True),
    ("https://open.spotify.com/album/64LU4c1nfjz1t4VnGhagcg", True),
    ("https://open.spotify.com/intl-de/album/64LU4c1nfjz1t4VnGhagcg", True),
    ("https://open.spotify.com/track/0eAuGrXyGFYwur9ARUe7LJ", False),
    ("https://music.apple.com/us/playlist/x/pl.f4d106fed2bd41149aaacabb233eb5eb", True),
    ("https://music.apple.com/us/playlist/x/pl.u-b3b889giyoEdXkB", True),
    ("https://music.apple.com/us/album/1989-taylors-version/1708308989", True),
    ("https://music.apple.com/us/album/style/1708308989?i=1708309009", False),
    ("https://music.youtube.com/playlist?list=PLx", True),
    ("https://www.youtube.com/playlist?list=PLx", True),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", False),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123", False),
    ("not a url", False),
])
def test_is_playlist_url(url, expected):
    assert is_playlist_url(url) is expected


# --- Apple Music (serialized-server-data) ---

def apple_server_data_html(sections):
    payload = {"data": [{"data": {"sections": sections}}]}
    return (
        '<html><script type="fastboot/shoebox" id="serialized-server-data">'
        + json.dumps(payload)
        + '</script></html>'
    )


def test_parse_apple_server_data():
    html = apple_server_data_html([
        {"itemKind": "containerDetailHeaderLockup", "items": [{"title": "My List"}]},
        {"itemKind": "trackLockup", "items": [
            {"title": "Song A", "artistName": "Artist A"},
            {"title": "Song B", "artistName": "Artist B"},
        ]},
        {"itemKind": "bubbleLockup", "items": [{"title": "Unrelated"}]},
    ])

    playlist = _parse_apple_server_data(html)
    assert playlist.name == "My List"
    assert [t.title for t in playlist.tracks] == ["Song A — Artist A", "Song B — Artist B"]
    assert playlist.tracks[0].query == "ytsearch1:Artist A Song A"


def test_parse_apple_server_data_missing_returns_none():
    assert _parse_apple_server_data("<html>nothing here</html>") is None


def test_parse_apple_server_data_no_tracks_returns_none():
    html = apple_server_data_html([{"itemKind": "spacer", "items": []}])
    assert _parse_apple_server_data(html) is None


# --- Spotify (embed page) ---

def spotify_embed_html(entity):
    payload = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
    return (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + '</script></html>'
    )


def test_resolve_spotify(monkeypatch):
    html = spotify_embed_html({
        "name": "Test Mix",
        "trackList": [
            {"title": "Track 1", "subtitle": "Artist 1"},
            {"title": "Track 2", "subtitle": "Artist 2"},
        ],
    })
    monkeypatch.setattr(playlist_resolver, '_fetch_page', lambda url: html)

    playlist = _resolve_spotify("https://open.spotify.com/playlist/abc123")
    assert playlist.name == "Test Mix"
    assert playlist.tracks[0].query == "ytsearch1:Artist 1 Track 1"
    assert playlist.tracks[1].title == "Track 2 — Artist 2"


def test_resolve_spotify_bad_page(monkeypatch):
    monkeypatch.setattr(playlist_resolver, '_fetch_page', lambda url: "<html></html>")
    with pytest.raises(RuntimeError):
        _resolve_spotify("https://open.spotify.com/playlist/abc123")


# --- YouTube (yt-dlp flat extraction) ---

def test_resolve_youtube(monkeypatch):
    info = {
        'title': 'YT Mix',
        'entries': [
            {'id': 'a1', 'title': 'Video 1', 'url': 'https://www.youtube.com/watch?v=a1'},
            None,  # yt-dlp emits None for unavailable entries
            {'id': 'b2', 'title': 'Video 2', 'url': None},
        ],
    }
    monkeypatch.setattr(playlist_resolver.yt_dlp, 'YoutubeDL', FakeYDL(info))

    playlist = _resolve_youtube("https://www.youtube.com/playlist?list=PLx")
    assert playlist.name == "YT Mix"
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0].query == "https://www.youtube.com/watch?v=a1"
    # Falls back to building a watch URL from the id
    assert playlist.tracks[1].query == "https://www.youtube.com/watch?v=b2"


def test_resolve_playlist_empty_raises(monkeypatch):
    monkeypatch.setattr(playlist_resolver.yt_dlp, 'YoutubeDL', FakeYDL({'title': 'Empty', 'entries': []}))
    with pytest.raises(RuntimeError, match="couldn't find any tracks"):
        resolve_playlist("https://www.youtube.com/playlist?list=PLx")
