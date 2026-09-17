"""Tests for the No Steely Dan policy."""

import asyncio
import importlib
from collections import deque
from types import SimpleNamespace

import pytest

import music_manager
import steely_dan
from music_manager import MusicManager, QueuedTrack
from playlist_resolver import PlaylistTrack, ResolvedPlaylist
from playlist_store import PlaylistStore
from commands.play import play
from commands.playnext import playnext
from commands.saved_playlists import loadq
from conftest import FakeVoiceClient, FakeChannel, FakeClient, FakeYDL, make_ctx

# commands/__init__ re-exports the play() function under the same name as its
# module, so go through importlib to patch the module's globals
play_module = importlib.import_module('commands.play')


def track(title, **kwargs):
    defaults = dict(url=f"https://yt/{title}", requester_id=42, channel_id=100)
    defaults.update(kwargs)
    return QueuedTrack(title=title, **defaults)


@pytest.fixture
def mm():
    return MusicManager()


@pytest.fixture
def ctx(mm):
    return make_ctx(music_manager=mm)


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly if anything reaches for yt-dlp — refusals must be free."""
    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL',
                        FakeYDL(error=AssertionError("yt-dlp should not be called")))


def is_refusal(message):
    return message in steely_dan.REFUSALS


# --- detection ---

@pytest.mark.parametrize("text", [
    "steely dan peg",
    "Steely Dan - Reelin' In The Years (Official Audio)",
    "STEELY DAN",
    "steelydan aja",
    "steely-dan",
    "Peg — Steely Dan",
    "ytsearch1:Steely Dan Deacon Blues",
])
def test_detects_the_dan(text):
    assert steely_dan.is_steely_dan(text)


@pytest.mark.parametrize("text", [
    "dan steely",
    "steel dan",
    "steely",
    "danny steel and the steelers",
    "aespa whiplash",
    "",
    None,
])
def test_leaves_innocents_alone(text):
    assert not steely_dan.is_steely_dan(text)


def test_detects_from_extraction_metadata():
    assert steely_dan.is_steely_dan_info({'title': 'Peg', 'uploader': 'Steely Dan - Topic'})
    assert steely_dan.is_steely_dan_info({'title': 'Peg', 'artists': ['Steely Dan']})
    assert steely_dan.is_steely_dan_info({'title': 'Peg', 'artist': 'Steely Dan'})
    assert steely_dan.is_steely_dan_info({'title': 'Peg', 'channel': 'Steely Dan'})
    assert not steely_dan.is_steely_dan_info({'title': 'Peg', 'uploader': 'Some Cover Band'})
    assert not steely_dan.is_steely_dan_info({})


def test_purge_and_note():
    tracks = [
        PlaylistTrack(query="q1", title="Peg — Steely Dan"),
        PlaylistTrack(query="q2", title="Whiplash — aespa"),
        PlaylistTrack(query="q3", title="Deacon Blues — Steely Dan"),
    ]
    kept, dropped = steely_dan.purge(tracks)
    assert [t.title for t in kept] == ["Whiplash — aespa"]
    assert dropped == 2
    assert "2 Steely Dan tracks" in steely_dan.playlist_note(2)
    assert "1 Steely Dan track " in steely_dan.playlist_note(1)
    assert steely_dan.playlist_note(0) == ""


def test_error_message_is_a_refusal():
    assert is_refusal(str(steely_dan.SteelyDanError()))
    assert str(steely_dan.SteelyDanError("custom")) == "custom"


# --- commands ---

def test_play_refuses_search_terms(mm, ctx, no_network):
    mm.voice_clients[1] = FakeVoiceClient()
    message = asyncio.run(play(ctx, "steely dan peg"))
    assert is_refusal(message)
    assert not mm.queues.get(1)


def test_playnext_refuses_too(mm, ctx, no_network):
    mm.voice_clients[1] = FakeVoiceClient()
    message = asyncio.run(playnext(ctx, "Steely Dan - Do It Again"))
    assert is_refusal(message)
    assert not mm.queues.get(1)


def test_play_refuses_streaming_link_that_resolves_to_the_dan(mm, ctx, no_network, monkeypatch):
    """odesli's search fallback carries the artist name back in."""
    monkeypatch.setattr(play_module, 'resolve_streaming_url',
                        lambda url: "ytsearch1:Steely Dan Peg")
    mm.voice_clients[1] = FakeVoiceClient()
    message = asyncio.run(play(ctx, "https://open.spotify.com/track/abc123"))
    assert is_refusal(message)
    assert not mm.queues.get(1)


def test_add_to_queue_refuses_by_metadata(mm, monkeypatch):
    """A direct YouTube link gives nothing away until yt-dlp tells us."""
    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL({
        'title': 'Peg (Official Audio)',
        'uploader': 'Steely Dan - Topic',
        'webpage_url': 'https://yt/peg',
        'url': 'https://stream/peg',
        'duration': 237,
    }))

    success, message = asyncio.run(mm.add_to_queue(1, "https://yt/peg", 42, channel_id=100))
    assert success is False
    assert is_refusal(message)
    assert not mm.queues.get(1)
    assert not vc.is_playing()


def test_play_playlist_tosses_the_dan_overboard(mm, ctx, monkeypatch):
    playlist = ResolvedPlaylist(name="Yacht Rock Essentials", tracks=[
        PlaylistTrack(query="ytsearch1:Toto Africa", title="Africa — Toto"),
        PlaylistTrack(query="ytsearch1:Steely Dan Peg", title="Peg — Steely Dan"),
        PlaylistTrack(query="ytsearch1:Hall Oates", title="Rich Girl — Daryl Hall & John Oates"),
    ])
    monkeypatch.setattr(play_module, 'resolve_playlist', lambda url: playlist)
    vc = FakeVoiceClient()
    vc._playing = True
    mm.voice_clients[1] = vc

    message = asyncio.run(play(ctx, "https://open.spotify.com/playlist/abc"))
    assert message == ("queued 2 tracks from **Yacht Rock Essentials** "
                       "(tossed 1 Steely Dan track overboard, you're welcome)")
    assert [t.title for t in mm.queues[1]] == ["Africa — Toto", "Rich Girl — Daryl Hall & John Oates"]


def test_play_playlist_all_dan_queues_nothing(mm, ctx, monkeypatch):
    playlist = ResolvedPlaylist(name="Aja", tracks=[
        PlaylistTrack(query="ytsearch1:Steely Dan Black Cow", title="Black Cow — Steely Dan"),
        PlaylistTrack(query="ytsearch1:Steely Dan Aja", title="Aja — Steely Dan"),
    ])
    monkeypatch.setattr(play_module, 'resolve_playlist', lambda url: playlist)
    mm.voice_clients[1] = FakeVoiceClient()

    message = asyncio.run(play(ctx, "https://open.spotify.com/album/aja"))
    assert message.startswith("**Aja** is wall-to-wall Steely Dan. queued nothing. ")
    assert any(message.endswith(r) for r in steely_dan.REFUSALS)
    assert not mm.queues.get(1)


def test_loadq_purges_pre_ban_contraband(mm, tmp_path):
    store = PlaylistStore(str(tmp_path / "playlists.json"))
    store.save_playlist(1, "old mix", [
        {"url": "https://yt/a", "title": "Fine Song"},
        {"url": "https://yt/b", "title": "Kid Charlemagne — Steely Dan"},
    ])
    ctx = make_ctx(music_manager=mm, playlist_store=store)
    vc = FakeVoiceClient()
    vc._playing = True
    mm.voice_clients[1] = vc

    message = asyncio.run(loadq(ctx, "old mix"))
    assert message == ("queued 1 tracks from **old mix** "
                       "(tossed 1 Steely Dan track overboard, you're welcome)")
    assert [t.title for t in mm.queues[1]] == ["Fine Song"]


# --- playback-time enforcement ---

def test_play_next_skips_lazy_playlist_track(mm, monkeypatch):
    """Playlist tracks are only titled at queue time; refuse at play time and move on."""
    client = FakeClient()
    channel = client.add_channel(FakeChannel(100))
    mm.client = client
    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    mm.queues[1] = deque([
        track("Peg — Steely Dan", url="ytsearch1:Steely Dan Peg"),
        track("Fine Song", url="https://yt/fine"),
    ])

    extracted = []

    def info_for(url):
        extracted.append(url)
        return {'title': 'Fine Song', 'url': 'https://stream/fine', 'id': 'fine', 'duration': 100}

    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(info_for))
    monkeypatch.setattr(music_manager.discord, 'FFmpegPCMAudio', lambda url, **kw: SimpleNamespace(url=url))
    monkeypatch.setattr(music_manager.discord, 'PCMVolumeTransformer',
                        lambda source, volume=1.0: source)

    assert asyncio.run(mm._play_next(1)) is True
    assert mm.now_playing[1].title == "Fine Song"
    assert extracted == ["https://yt/fine"]          # the Dan never hit the network
    assert len(channel.sent) == 1
    assert channel.sent[0].startswith("skipping **Peg — Steely Dan** — ")
    assert any(channel.sent[0].endswith(r) for r in steely_dan.REFUSALS)


def test_play_next_refuses_by_metadata(mm, monkeypatch):
    """A URL with an innocent title still gets caught by the extraction metadata."""
    client = FakeClient()
    channel = client.add_channel(FakeChannel(100))
    mm.client = client
    mm.voice_clients[1] = FakeVoiceClient()
    mm.queues[1] = deque([track("Totally Not Steely Dan", url="https://yt/sneaky")])

    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL({
        'title': 'Peg', 'artist': 'Steely Dan', 'url': 'https://stream/peg', 'id': 'peg',
    }))

    assert asyncio.run(mm._play_next(1)) is False
    assert mm.now_playing[1] is None
    assert len(channel.sent) == 1
    assert "skipping **Totally Not Steely Dan**" in channel.sent[0]


def test_autoplay_skips_the_dan(mm, monkeypatch):
    mm._last_video_id[1] = 'seed'
    mm._last_track[1] = track("Seed Song")

    mix = {'entries': [
        {'id': 'seed', 'title': 'Seed Song', 'url': 'https://yt/seed'},
        {'id': 'dan1', 'title': 'Steely Dan - Peg', 'url': 'https://yt/dan1'},
        {'id': 'dan2', 'title': 'Peg', 'uploader': 'Steely Dan - Topic', 'url': 'https://yt/dan2'},
        {'id': 'fresh', 'title': 'Fresh Track', 'url': 'https://yt/fresh'},
    ]}
    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(mix))

    picked = mm._pick_autoplay_track(1)
    assert picked.url == 'https://yt/fresh'
