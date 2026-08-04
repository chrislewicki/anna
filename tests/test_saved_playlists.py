"""Tests for the playlist store and saveq/loadq/playlists/delq commands."""

import asyncio
from collections import deque

import pytest

from music_manager import MusicManager, QueuedTrack
from playlist_store import PlaylistStore
from commands.saved_playlists import saveq, loadq, playlists, delq
from conftest import FakeVoiceClient, make_ctx


def track(title):
    return QueuedTrack(url=f"https://yt/{title}", title=title, requester_id=42)


@pytest.fixture
def store(tmp_path):
    return PlaylistStore(str(tmp_path / "playlists.json"))


@pytest.fixture
def mm():
    return MusicManager()


@pytest.fixture
def ctx(mm, store):
    return make_ctx(music_manager=mm, playlist_store=store)


# --- store ---

def test_store_round_trip(store, tmp_path):
    store.save_playlist(1, "My Mix", [{"url": "u1", "title": "t1"}])
    assert store.get_playlist(1, "my mix")["name"] == "My Mix"

    # Survives reload from disk
    reloaded = PlaylistStore(str(tmp_path / "playlists.json"))
    assert reloaded.get_playlist(1, "MY MIX")["tracks"] == [{"url": "u1", "title": "t1"}]


def test_store_per_guild_isolation(store):
    store.save_playlist(1, "mix", [{"url": "u", "title": "t"}])
    assert store.get_playlist(2, "mix") is None


def test_store_delete(store):
    store.save_playlist(1, "mix", [{"url": "u", "title": "t"}])
    assert store.delete_playlist(1, "MIX") is True
    assert store.delete_playlist(1, "mix") is False
    assert store.get_playlist(1, "mix") is None


def test_store_list_sorted(store):
    store.save_playlist(1, "zeta", [])
    store.save_playlist(1, "Alpha", [])
    names = [p["name"] for p in store.list_playlists(1)]
    assert names == ["Alpha", "zeta"]


# --- commands ---

def test_saveq_includes_now_playing_and_queue(mm, ctx, store):
    mm.now_playing[1] = track("current")
    mm.queues[1] = deque([track("q1"), track("q2")])

    response = asyncio.run(saveq(ctx, "friday bangers"))
    assert "saved **friday bangers** (3 tracks)" == response

    saved = store.get_playlist(1, "friday bangers")
    assert [t["title"] for t in saved["tracks"]] == ["current", "q1", "q2"]


def test_saveq_empty(mm, ctx):
    assert "nothing to save" in asyncio.run(saveq(ctx, "empty"))


def test_saveq_usage(ctx):
    assert "usage" in asyncio.run(saveq(ctx, ""))


def test_loadq_queues_tracks(mm, ctx, store):
    store.save_playlist(1, "Mix", [
        {"url": "https://yt/a", "title": "a"},
        {"url": "https://yt/b", "title": "b"},
    ])
    vc = FakeVoiceClient()
    vc._playing = True  # prevent immediate playback extraction
    mm.voice_clients[1] = vc

    response = asyncio.run(loadq(ctx, "mix"))
    assert response == "queued 2 tracks from **Mix**"
    assert [t.title for t in mm.queues[1]] == ["a", "b"]
    assert mm.queues[1][0].channel_id == 100


def test_loadq_missing(ctx, mm):
    mm.voice_clients[1] = FakeVoiceClient()
    assert "no saved playlist" in asyncio.run(loadq(ctx, "ghost"))


def test_playlists_listing(ctx, store):
    assert "no saved playlists" in asyncio.run(playlists(ctx, ""))
    store.save_playlist(1, "Mix", [{"url": "u", "title": "t"}])
    response = asyncio.run(playlists(ctx, ""))
    assert "Mix (1 tracks)" in response


def test_delq(ctx, store):
    store.save_playlist(1, "Mix", [])
    assert "deleted" in asyncio.run(delq(ctx, "mix"))
    assert "no saved playlist" in asyncio.run(delq(ctx, "mix"))
