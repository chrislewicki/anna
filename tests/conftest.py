"""Shared test fixtures and fakes for Anna bot tests."""

import os
import sys
from types import SimpleNamespace

# Make the repo root importable (modules are top-level, not a package)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeVoiceClient:
    """Duck-typed stand-in for discord.VoiceClient."""

    def __init__(self, members=None):
        self._playing = False
        self._paused = False
        self.source = None
        self.channel = SimpleNamespace(members=members if members is not None else [])
        self._after = None

    def is_playing(self):
        return self._playing

    def is_paused(self):
        return self._paused

    def play(self, source, after=None):
        self._playing = True
        self.source = source
        self._after = after

    def pause(self):
        self._playing = False
        self._paused = True

    def resume(self):
        self._playing = True
        self._paused = False

    def stop(self):
        self._playing = False
        self._paused = False


class FakeChannel:
    """Text channel that records sent messages."""

    def __init__(self, channel_id=100):
        self.id = channel_id
        self.sent = []

    async def send(self, text):
        self.sent.append(text)


class FakeClient:
    """Discord client stand-in exposing get_channel()."""

    def __init__(self):
        self.channels = {}

    def add_channel(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class FakeYDL:
    """Stand-in for yt_dlp.YoutubeDL returning canned info (or raising)."""

    def __init__(self, info=None, error=None):
        self.info = info
        self.error = error

    def __call__(self, opts=None):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=False):
        if self.error:
            raise self.error
        if callable(self.info):
            return self.info(url)
        return self.info


def make_ctx(guild_id=1, user_id=42, channel_id=100, music_manager=None,
             reminder_manager=None, playlist_store=None, voice=None):
    """Build a CommandContext-shaped object for invoking command handlers."""
    message = SimpleNamespace(
        guild=SimpleNamespace(id=guild_id),
        author=SimpleNamespace(id=user_id, voice=voice),
        channel=SimpleNamespace(id=channel_id),
        content="",
    )
    return SimpleNamespace(
        message=message,
        music_manager=music_manager,
        reminder_manager=reminder_manager,
        playlist_store=playlist_store,
    )
