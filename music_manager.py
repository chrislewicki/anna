"""Music playback and voice connection management."""

import asyncio
import logging
from typing import Optional, Dict
from collections import deque
from dataclasses import dataclass
import discord
import yt_dlp

logger = logging.getLogger(__name__)

# yt-dlp configuration
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

# FFmpeg options for Discord streaming
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


@dataclass
class QueuedTrack:
    """Represents a track in the queue."""
    url: str
    title: str
    requester_id: int
    duration: Optional[int] = None


class MusicManager:
    """Manages voice connections and music playback."""

    def __init__(self):
        """Initialize music manager."""
        self.voice_clients: Dict[int, discord.VoiceClient] = {}
        # guild_id -> VoiceClient mapping

        self.queues: Dict[int, deque] = {}
        # guild_id -> queue of QueuedTrack

        self.now_playing: Dict[int, Optional[QueuedTrack]] = {}
        # guild_id -> currently playing track

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        # Event loop reference for thread-safe callback execution

    async def join_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
        """
        Join a voice channel.

        Args:
            voice_channel: The voice channel to join

        Returns:
            VoiceClient for the connection

        Raises:
            discord.ClientException: If already connected to voice in this guild
        """
        guild_id = voice_channel.guild.id

        # If already connected to this guild, disconnect first
        if guild_id in self.voice_clients:
            await self.leave_channel(guild_id)

        try:
            voice_client = await voice_channel.connect()
            self.voice_clients[guild_id] = voice_client
            logger.info(f"Connected to voice channel {voice_channel.name} in guild {guild_id}")
            return voice_client
        except Exception as e:
            logger.error(f"Failed to join voice channel: {e}", exc_info=True)
            raise

    async def leave_channel(self, guild_id: int) -> bool:
        """
        Leave the voice channel in a guild.

        Args:
            guild_id: The guild ID to leave voice from

        Returns:
            True if disconnected, False if not connected
        """
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client:
            return False

        try:
            await voice_client.disconnect()
            del self.voice_clients[guild_id]

            # Clear queue and now_playing when leaving
            self.queues.pop(guild_id, None)
            self.now_playing.pop(guild_id, None)

            logger.info(f"Disconnected from voice in guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error leaving voice channel: {e}", exc_info=True)
            return False

    def get_voice_client(self, guild_id: int) -> Optional[discord.VoiceClient]:
        """Get the voice client for a guild."""
        return self.voice_clients.get(guild_id)

    async def add_to_queue(self, guild_id: int, url: str, requester_id: int) -> tuple[bool, str]:
        """
        Add a track to the queue and start playing if nothing is playing.

        Args:
            guild_id: Guild ID
            url: URL to audio source
            requester_id: Discord user ID who requested

        Returns:
            Tuple of (success: bool, message: str)
        """
        voice_client = self.get_voice_client(guild_id)
        if not voice_client:
            return False, "not connected to voice channel"

        try:
            # Extract track info (title, duration, etc.)
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                logger.info(f"Extracting info from: {url}")
                info = ydl.extract_info(url, download=False)

                # Handle search results (ytsearch:) vs direct URLs
                if 'entries' in info:
                    # Search result - get first entry
                    info = info['entries'][0]

                title = info.get('title', 'Unknown')
                duration = info.get('duration')  # Can be None
                # Store the actual video URL, not the search query
                video_url = info.get('webpage_url') or info.get('url') or url

            # Create queued track
            track = QueuedTrack(
                url=video_url,
                title=title,
                requester_id=requester_id,
                duration=duration
            )

            # Initialize queue for guild if doesn't exist
            if guild_id not in self.queues:
                self.queues[guild_id] = deque()

            # Add to queue
            self.queues[guild_id].append(track)
            logger.info(f"Added to queue in guild {guild_id}: {title}")

            # If nothing is playing, start playing
            if not voice_client.is_playing() and not voice_client.is_paused():
                await self._play_next(guild_id)
                return True, f"now playing: {title}"
            else:
                queue_position = len(self.queues[guild_id])
                return True, f"added to queue: {title} (position {queue_position})"

        except Exception as e:
            logger.error(f"Failed to add to queue: {e}", exc_info=True)
            return False, f"failed to add to queue: {str(e)}"

    async def _play_next(self, guild_id: int) -> bool:
        """
        Play the next track in queue.

        Args:
            guild_id: Guild ID

        Returns:
            True if started playing, False if queue empty or error
        """
        voice_client = self.get_voice_client(guild_id)
        if not voice_client:
            return False

        # Get next track from queue
        queue = self.queues.get(guild_id)
        if not queue or len(queue) == 0:
            logger.info(f"Queue empty in guild {guild_id}")
            self.now_playing[guild_id] = None
            return False

        track = queue.popleft()
        self.now_playing[guild_id] = track

        try:
            # Extract audio URL (need fresh URL each time, they expire)
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(track.url, download=False)
                audio_url = info['url']

            # Create audio source
            audio_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

            # Store event loop reference if not already stored
            if not self.loop:
                self.loop = asyncio.get_running_loop()

            # Start playback with callback
            voice_client.play(
                audio_source,
                after=lambda e: self._playback_finished(guild_id, e)
            )

            logger.info(f"Now playing in guild {guild_id}: {track.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to play track: {e}", exc_info=True)
            self.now_playing[guild_id] = None
            # Try to play next track if this one failed
            if self.loop:
                asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.loop)
            return False

    async def play_url(self, guild_id: int, url: str) -> bool:
        """
        Play audio from a URL.

        Args:
            guild_id: The guild ID where music should play
            url: URL to audio/video source

        Returns:
            True if started playing, False otherwise
        """
        voice_client = self.get_voice_client(guild_id)
        if not voice_client:
            logger.warning(f"No voice client for guild {guild_id}")
            return False

        try:
            # Stop current playback if any
            if voice_client.is_playing():
                voice_client.stop()

            # Extract audio info with yt-dlp
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                logger.info(f"Extracting audio info from: {url}")
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'Unknown')

            # Create audio source
            audio_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

            # Start playback
            voice_client.play(audio_source, after=lambda e: self._playback_finished(guild_id, e))
            logger.info(f"Now playing: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to play audio: {e}", exc_info=True)
            return False

    def _playback_finished(self, guild_id: int, error):
        """
        Callback when audio playback finishes.

        NOTE: This runs in a thread pool, NOT the event loop!
        Must use asyncio.run_coroutine_threadsafe() to call async functions.
        """
        if error:
            logger.error(f"Playback error in guild {guild_id}: {error}")
        else:
            logger.info(f"Playback finished in guild {guild_id}")

        # Clear current track
        self.now_playing[guild_id] = None

        # Play next track if available
        if self.loop:
            # Schedule _play_next() to run in the event loop
            asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.loop)
        else:
            logger.error(f"No event loop reference, cannot auto-play next track in guild {guild_id}")

    def pause(self, guild_id: int) -> bool:
        """Pause playback."""
        voice_client = self.get_voice_client(guild_id)
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            return True
        return False

    def resume(self, guild_id: int) -> bool:
        """Resume playback."""
        voice_client = self.get_voice_client(guild_id)
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            return True
        return False

    def stop(self, guild_id: int) -> bool:
        """Stop playback."""
        voice_client = self.get_voice_client(guild_id)
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            return True
        return False
