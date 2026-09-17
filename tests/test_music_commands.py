"""Tests for music command handlers (remove, move, playnext, loop, volume, etc.)."""

import asyncio
import time
from collections import deque
from types import SimpleNamespace

import pytest

import music_manager
from music_manager import MusicManager, QueuedTrack
from commands.remove import remove
from commands.move import move
from commands.playnext import playnext
from commands.loop import loop
from commands.volume import volume
from commands.autoplay import autoplay
from commands.skip import skip
from commands.stop import stop
from commands.play import play
from commands.nowplaying import nowplaying
from commands.shuffle import shuffle
from conftest import FakeVoiceClient, FakeYDL, make_ctx


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


# --- remove / move ---

def test_remove_command(mm, ctx):
    mm.queues[1] = deque([track("a"), track("b")])
    assert asyncio.run(remove(ctx, "2")) == "removed: b"
    assert asyncio.run(remove(ctx, "9")) == "no track at position 9 — check `@Anna queue`"
    assert "usage" in asyncio.run(remove(ctx, "abc"))


def test_move_command(mm, ctx):
    mm.queues[1] = deque([track("a"), track("b"), track("c")])
    response = asyncio.run(move(ctx, "3 1"))
    assert response == "moved to position 1: c"
    assert [t.title for t in mm.queues[1]] == ["c", "a", "b"]
    assert "usage" in asyncio.run(move(ctx, "3"))
    assert "invalid positions" in asyncio.run(move(ctx, "1 99"))


# --- playnext ---

def test_playnext_front_queues(mm, ctx, monkeypatch):
    vc = FakeVoiceClient()
    vc._playing = True
    mm.voice_clients[1] = vc
    mm.queues[1] = deque([track("existing")])

    def info_for(url):
        if url.startswith("ytsearch"):
            return {'entries': [{'id': 'j1', 'url': 'https://yt/jumped', 'title': 'Jumped'}]}
        return {'title': 'Jumped', 'webpage_url': 'https://yt/jumped', 'duration': 60}

    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(info_for))

    response = asyncio.run(playnext(ctx, "some song"))
    assert response == "up next: Jumped"
    assert mm.queues[1][0].title == "Jumped"
    assert mm.queues[1][1].title == "existing"


def test_playnext_rejects_playlists(ctx):
    response = asyncio.run(playnext(ctx, "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"))
    assert "use `@Anna play`" in response


def test_playnext_usage(ctx):
    assert "usage" in asyncio.run(playnext(ctx, ""))


# --- loop ---

def test_loop_command(mm, ctx):
    assert asyncio.run(loop(ctx, "")) == "loop mode: **off**"
    assert asyncio.run(loop(ctx, "track")) == "looping the track"
    assert mm.get_loop_mode(1) == "track"
    assert asyncio.run(loop(ctx, "queue")) == "looping the queue"
    assert asyncio.run(loop(ctx, "off")) == "loop off"
    assert "usage" in asyncio.run(loop(ctx, "sideways"))


# --- volume ---

def test_volume_command(mm, ctx):
    assert asyncio.run(volume(ctx, "")) == "volume: **100%**"
    assert asyncio.run(volume(ctx, "50")) == "volume set to **50%**"
    assert mm.get_volume(1) == 0.5
    assert asyncio.run(volume(ctx, "")) == "volume: **50%**"
    assert "between 0 and 200" in asyncio.run(volume(ctx, "500"))
    assert "usage" in asyncio.run(volume(ctx, "loud"))


def test_volume_accepts_percent_sign(mm, ctx):
    assert asyncio.run(volume(ctx, "75%")) == "volume set to **75%**"


# --- autoplay ---

def test_autoplay_command(mm, ctx):
    response = asyncio.run(autoplay(ctx, ""))
    assert "**on**" in response
    assert mm.get_autoplay(1) is True
    assert "**off**" in asyncio.run(autoplay(ctx, ""))
    assert "**on**" in asyncio.run(autoplay(ctx, "on"))
    assert "**off**" in asyncio.run(autoplay(ctx, "off"))
    assert "usage" in asyncio.run(autoplay(ctx, "maybe"))


# --- skip ---

def test_skip_command(mm, ctx):
    assert asyncio.run(skip(ctx, "")) == "not in a voice channel"

    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    assert asyncio.run(skip(ctx, "")) == "nothing is playing"

    vc._playing = True
    mm.now_playing[1] = track("current")
    mm.queues[1] = deque([track("next")])
    assert asyncio.run(skip(ctx, "")) == "skipped: current"
    assert 1 in mm._skipped


# --- streaming resolution (odesli search fallback) ---

def test_resolve_single_query_no_double_search_prefix(monkeypatch):
    """Odesli falling back to a ytsearch1: query must not get prefixed again."""
    import importlib
    play_module = importlib.import_module('commands.play')

    monkeypatch.setattr(play_module, 'resolve_streaming_url',
                        lambda url: "ytsearch1:Ninajirachi Song Title")

    result = play_module._resolve_single_query(
        "https://music.apple.com/us/album/song/1824602984?i=1824602992")
    assert result == "ytsearch1:Ninajirachi Song Title"


def test_resolve_single_query_search_terms_still_prefixed():
    import importlib
    play_module = importlib.import_module('commands.play')
    assert play_module._resolve_single_query("aespa whiplash") == "ytsearch1:aespa whiplash"


def test_add_to_queue_empty_search_is_friendly(mm, ctx, monkeypatch):
    """A search with no results should return a message, not crash."""
    vc = FakeVoiceClient()
    vc._playing = True
    mm.voice_clients[1] = vc

    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL({'entries': []}))

    success, message = asyncio.run(mm.add_to_queue(1, "ytsearch1:gibberish query", 42))
    assert success is False
    assert message == "couldn't find anything for: gibberish query"
    assert not mm.queues.get(1)


# --- stop / bare play resume ---

def test_stop_command_reports_queue(mm, ctx):
    vc = FakeVoiceClient()
    vc._playing = True
    mm.voice_clients[1] = vc
    mm.now_playing[1] = track("current")
    mm.queues[1] = deque([track("next"), track("later")])

    response = asyncio.run(stop(ctx, ""))
    assert response == "stopped playback — 3 track(s) still queued, `@Anna play` to resume"


def test_stop_command_nothing_playing(mm, ctx):
    mm.voice_clients[1] = FakeVoiceClient()
    assert asyncio.run(stop(ctx, "")) == "nothing is playing"


def test_bare_play_resumes_stopped_queue(mm, ctx, monkeypatch):
    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    mm.queues[1] = deque([track("halted")])

    import discord
    from types import SimpleNamespace as NS
    monkeypatch.setattr(discord, 'FFmpegPCMAudio', lambda url, **kw: NS(url=url))
    monkeypatch.setattr(discord, 'PCMVolumeTransformer',
                        lambda source, volume=1.0: NS(source=source, volume=volume))
    info = {'url': 'http://audio', 'id': 'v1', 'title': 'halted', 'duration': 60}
    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(info))

    response = asyncio.run(play(ctx, ""))
    assert response == "resuming the queue: halted"


def test_bare_play_empty_queue_shows_usage(mm, ctx):
    mm.voice_clients[1] = FakeVoiceClient()
    assert "usage" in asyncio.run(play(ctx, ""))


# --- nowplaying progress ---

def test_nowplaying_progress(mm, ctx):
    playing = track("Song")
    playing.duration = 100
    playing.started_at = time.time() - 30
    mm.now_playing[1] = playing

    response = asyncio.run(nowplaying(ctx, ""))
    assert "**progress:** 0:30 / 1:40" in response
    assert "<@42>" in response


def test_nowplaying_elapsed_caps_at_duration(mm, ctx):
    playing = track("Song")
    playing.duration = 100
    playing.started_at = time.time() - 500
    mm.now_playing[1] = playing

    response = asyncio.run(nowplaying(ctx, ""))
    assert "1:40 / 1:40" in response


def test_nowplaying_nothing(mm, ctx):
    assert "nothing" in asyncio.run(nowplaying(ctx, ""))


# --- shuffle ---

def test_shuffle_command(mm, ctx):
    assert "empty" in asyncio.run(shuffle(ctx, ""))
    mm.queues[1] = deque([track("only")])
    assert "only one track" in asyncio.run(shuffle(ctx, ""))
    mm.queues[1] = deque([track("a"), track("b"), track("c")])
    assert asyncio.run(shuffle(ctx, "")) == "shuffled 3 queued tracks"
