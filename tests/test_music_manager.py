"""Tests for MusicManager queue operations, loop modes, idle detection, and playback."""

import asyncio
import time
from collections import deque
from types import SimpleNamespace

import pytest

import music_manager
from music_manager import MusicManager, QueuedTrack
from conftest import FakeVoiceClient, FakeChannel, FakeClient, FakeYDL


def track(title, **kwargs):
    defaults = dict(url=f"https://yt/{title}", requester_id=42, channel_id=100)
    defaults.update(kwargs)
    return QueuedTrack(title=title, **defaults)


@pytest.fixture
def mm():
    return MusicManager()


class FakeVolumeSource:
    def __init__(self, source, volume=1.0):
        self.source = source
        self.volume = volume


@pytest.fixture
def patched_audio(monkeypatch):
    """Replace discord audio classes so no ffmpeg process is spawned."""
    monkeypatch.setattr(music_manager.discord, 'FFmpegPCMAudio',
                        lambda url, **kw: SimpleNamespace(url=url))
    monkeypatch.setattr(music_manager.discord, 'PCMVolumeTransformer', FakeVolumeSource)


# --- queue operations ---

def test_remove_from_queue(mm):
    mm.queues[1] = deque([track("a"), track("b"), track("c")])
    removed = mm.remove_from_queue(1, 2)
    assert removed.title == "b"
    assert [t.title for t in mm.queues[1]] == ["a", "c"]


def test_remove_invalid_position(mm):
    mm.queues[1] = deque([track("a")])
    assert mm.remove_from_queue(1, 0) is None
    assert mm.remove_from_queue(1, 2) is None
    assert mm.remove_from_queue(99, 1) is None
    assert len(mm.queues[1]) == 1


def test_move_in_queue(mm):
    mm.queues[1] = deque([track("a"), track("b"), track("c")])
    moved = mm.move_in_queue(1, 3, 1)
    assert moved.title == "c"
    assert [t.title for t in mm.queues[1]] == ["c", "a", "b"]


def test_move_invalid_positions(mm):
    mm.queues[1] = deque([track("a"), track("b")])
    assert mm.move_in_queue(1, 1, 5) is None
    assert mm.move_in_queue(1, 0, 1) is None
    assert [t.title for t in mm.queues[1]] == ["a", "b"]


def test_shuffle_preserves_tracks(mm):
    titles = [f"t{i}" for i in range(20)]
    mm.queues[1] = deque(track(t) for t in titles)
    count = mm.shuffle_queue(1)
    assert count == 20
    assert sorted(t.title for t in mm.queues[1]) == sorted(titles)


# --- skip and loop modes ---

def test_skip_returns_title_and_flags(mm):
    vc = FakeVoiceClient()
    vc._playing = True
    mm.voice_clients[1] = vc
    mm.now_playing[1] = track("current")

    title = mm.skip(1)
    assert title == "current"
    assert 1 in mm._skipped
    assert not vc.is_playing()


def test_skip_nothing_playing(mm):
    mm.voice_clients[1] = FakeVoiceClient()
    assert mm.skip(1) is None


def test_loop_track_requeues_at_front(mm):
    finished = track("looper")
    mm.now_playing[1] = finished
    mm.queues[1] = deque([track("next")])
    mm.set_loop_mode(1, 'track')

    mm._playback_finished(1, None)
    assert mm.queues[1][0] is finished
    assert mm.now_playing[1] is None


def test_loop_track_skip_moves_on(mm):
    finished = track("looper")
    mm.now_playing[1] = finished
    mm.queues[1] = deque([track("next")])
    mm.set_loop_mode(1, 'track')
    mm._skipped.add(1)

    mm._playback_finished(1, None)
    assert [t.title for t in mm.queues[1]] == ["next"]
    assert 1 not in mm._skipped


def test_loop_queue_requeues_at_end(mm):
    finished = track("first")
    mm.now_playing[1] = finished
    mm.queues[1] = deque([track("second")])
    mm.set_loop_mode(1, 'queue')

    mm._playback_finished(1, None)
    assert [t.title for t in mm.queues[1]] == ["second", "first"]


def test_loop_off_does_not_requeue(mm):
    mm.now_playing[1] = track("done")
    mm.queues[1] = deque()

    mm._playback_finished(1, None)
    assert len(mm.queues[1]) == 0


def test_set_loop_mode_validates(mm):
    with pytest.raises(ValueError):
        mm.set_loop_mode(1, 'forever')


# --- volume ---

def test_volume_default(mm):
    assert mm.get_volume(1) == 1.0


def test_set_volume_updates_live_source(mm):
    vc = FakeVoiceClient()
    vc.source = FakeVolumeSource(None, volume=1.0)
    mm.voice_clients[1] = vc

    mm.set_volume(1, 0.5)
    assert mm.get_volume(1) == 0.5
    assert vc.source.volume == 0.5


# --- idle detection ---

def test_check_idle_disconnects_after_timeout(mm):
    human = SimpleNamespace(bot=False)
    vc = FakeVoiceClient(members=[human])
    mm.voice_clients[1] = vc

    assert mm.check_idle(300, now=1000) == []      # idle timer starts
    assert mm.check_idle(300, now=1299) == []      # not yet
    assert mm.check_idle(300, now=1301) == [1]     # past timeout


def test_check_idle_playing_resets_timer(mm):
    human = SimpleNamespace(bot=False)
    vc = FakeVoiceClient(members=[human])
    mm.voice_clients[1] = vc

    mm.check_idle(300, now=1000)
    vc._playing = True
    assert mm.check_idle(300, now=1400) == []
    assert 1 not in mm._idle_since


def test_check_idle_alone_counts_even_while_playing(mm):
    bot_member = SimpleNamespace(bot=True)
    vc = FakeVoiceClient(members=[bot_member])
    vc._playing = True
    mm.voice_clients[1] = vc

    assert mm.check_idle(300, now=1000) == []
    assert mm.check_idle(300, now=1301) == [1]


def test_check_idle_paused_counts_as_active(mm):
    human = SimpleNamespace(bot=False)
    vc = FakeVoiceClient(members=[human])
    vc._paused = True
    mm.voice_clients[1] = vc

    assert mm.check_idle(300, now=1000) == []
    assert mm.check_idle(300, now=2000) == []


# --- playback (_play_next) ---

def test_play_next_search_result(mm, monkeypatch, patched_audio):
    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    mm.queues[1] = deque([track("Song", url="ytsearch1:artist song", duration=None)])
    mm.volumes[1] = 0.5

    info = {'entries': [{'url': 'http://audio', 'id': 'vid1', 'title': 'Song', 'duration': 100}]}
    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(info))

    assert asyncio.run(mm._play_next(1)) is True
    assert vc.is_playing()
    playing = mm.now_playing[1]
    assert playing.started_at is not None
    assert playing.duration == 100          # backfilled from extraction
    assert vc.source.volume == 0.5          # per-guild volume applied
    assert mm._last_video_id[1] == 'vid1'   # autoplay seed recorded


def test_play_next_failure_announces_and_continues(mm, monkeypatch, patched_audio):
    client = FakeClient()
    channel = client.add_channel(FakeChannel(100))
    mm.client = client

    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    mm.queues[1] = deque([track("Broken")])

    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(error=RuntimeError("boom")))

    assert asyncio.run(mm._play_next(1)) is False
    assert channel.sent == ["couldn't play **Broken**, skipping"]
    assert mm.now_playing[1] is None


def test_play_next_empty_search_skips_to_next(mm, monkeypatch, patched_audio):
    client = FakeClient()
    channel = client.add_channel(FakeChannel(100))
    mm.client = client

    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    mm.queues[1] = deque([
        track("NoResults", url="ytsearch1:gibberish"),
        track("Good", url="https://yt/good"),
    ])

    def info_for(url):
        if url.startswith("ytsearch1:"):
            return {'entries': []}
        return {'url': 'http://audio', 'id': 'vid2', 'title': 'Good', 'duration': 60}

    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(info_for))

    assert asyncio.run(mm._play_next(1)) is True
    assert "couldn't play **NoResults**" in channel.sent[0]
    assert mm.now_playing[1].title == "Good"


# --- autoplay ---

def test_pick_autoplay_track(mm, monkeypatch):
    mm._last_video_id[1] = 'seed'
    mm._last_track[1] = track("Seed Song")
    mm._recent_video_ids[1] = deque(['seed', 'old1'], maxlen=50)

    mix = {'entries': [
        {'id': 'seed', 'title': 'Seed Song', 'url': 'https://yt/seed'},
        {'id': 'old1', 'title': 'Already Played', 'url': 'https://yt/old1'},
        {'id': 'fresh', 'title': 'Fresh Track', 'url': 'https://yt/fresh'},
    ]}
    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(mix))

    picked = mm._pick_autoplay_track(1)
    assert picked is not None
    assert picked.url == 'https://yt/fresh'
    assert "(autoplay)" in picked.title
    assert picked.requester_id == 42
    assert picked.channel_id == 100


def test_pick_autoplay_without_seed(mm):
    assert mm._pick_autoplay_track(1) is None


def test_play_next_uses_autoplay_when_queue_empty(mm, monkeypatch, patched_audio):
    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc
    mm.set_autoplay(1, True)
    mm._last_video_id[1] = 'seed'
    mm._last_track[1] = track("Seed Song")

    def info_for(url):
        if 'list=RD' in url:
            return {'entries': [{'id': 'fresh', 'title': 'Fresh', 'url': 'https://yt/fresh'}]}
        return {'url': 'http://audio', 'id': 'fresh', 'title': 'Fresh', 'duration': 60}

    monkeypatch.setattr(music_manager.yt_dlp, 'YoutubeDL', FakeYDL(info_for))

    assert asyncio.run(mm._play_next(1)) is True
    assert "(autoplay)" in mm.now_playing[1].title


def test_play_next_no_autoplay_stops_on_empty(mm):
    vc = FakeVoiceClient()
    mm.voice_clients[1] = vc

    assert asyncio.run(mm._play_next(1)) is False
    assert mm.now_playing.get(1) is None


# --- bulk queueing ---

def test_add_playlist_to_queue_is_lazy(mm):
    vc = FakeVoiceClient()
    vc._playing = True  # prevent immediate _play_next
    mm.voice_clients[1] = vc

    entries = [SimpleNamespace(query=f"ytsearch1:song {i}", title=f"Song {i}") for i in range(50)]
    success, message = asyncio.run(mm.add_playlist_to_queue(1, entries, 42, channel_id=100))

    assert success
    assert "50" in message
    assert len(mm.queues[1]) == 50
    assert mm.queues[1][0].title == "Song 0"
    assert mm.queues[1][0].channel_id == 100
