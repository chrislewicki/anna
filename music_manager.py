"""Music playback and voice connection management."""

import asyncio
import logging
import random
import time
from typing import Optional, Dict, List
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

# Flat extraction for autoplay (YouTube mix) lookups
YDL_FLAT_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'extract_flat': 'in_playlist',
}

# FFmpeg options for Discord streaming
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af dynaudnorm',
}

LOOP_MODES = ('off', 'track', 'queue')

# Autoplay won't repeat any of the last N videos played in a guild
RECENT_TRACK_MEMORY = 50


@dataclass
class QueuedTrack:
    """Represents a track in the queue."""
    url: str
    title: str
    requester_id: int
    duration: Optional[int] = None
    channel_id: Optional[int] = None    # text channel for playback announcements
    started_at: Optional[float] = None  # unix timestamp when playback began


class MusicManager:
    """Manages voice connections and music playback."""

    def __init__(self, client: Optional[discord.Client] = None):
        """
        Initialize music manager.

        Args:
            client: Discord client, used to send playback announcements
                to text channels. Announcements are skipped if None.
        """
        self.client = client

        self.voice_clients: Dict[int, discord.VoiceClient] = {}
        # guild_id -> VoiceClient mapping

        self.queues: Dict[int, deque] = {}
        # guild_id -> queue of QueuedTrack

        self.now_playing: Dict[int, Optional[QueuedTrack]] = {}
        # guild_id -> currently playing track

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        # Event loop reference for thread-safe callback execution

        # Per-guild playback preferences (sticky across voice sessions)
        self.loop_modes: Dict[int, str] = {}    # 'off' | 'track' | 'queue'
        self.autoplay: Dict[int, bool] = {}
        self.volumes: Dict[int, float] = {}     # 0.0-2.0, default 1.0

        # Transient per-guild state
        self._skipped: set = set()              # guilds where current track was skipped
        self._stopped: set = set()              # guilds where playback was halted via stop()
        self._idle_since: Dict[int, float] = {}
        self._last_track: Dict[int, QueuedTrack] = {}
        self._last_video_id: Dict[int, str] = {}
        self._recent_video_ids: Dict[int, deque] = {}

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

            # Clear transient playback state (preferences like loop mode,
            # autoplay, and volume are kept)
            self.queues.pop(guild_id, None)
            self.now_playing.pop(guild_id, None)
            self._skipped.discard(guild_id)
            self._stopped.discard(guild_id)
            self._idle_since.pop(guild_id, None)
            self._last_track.pop(guild_id, None)
            self._last_video_id.pop(guild_id, None)
            self._recent_video_ids.pop(guild_id, None)

            logger.info(f"Disconnected from voice in guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error leaving voice channel: {e}", exc_info=True)
            return False

    def get_voice_client(self, guild_id: int) -> Optional[discord.VoiceClient]:
        """Get the voice client for a guild."""
        return self.voice_clients.get(guild_id)

    async def add_to_queue(
        self,
        guild_id: int,
        url: str,
        requester_id: int,
        channel_id: Optional[int] = None,
        play_next: bool = False
    ) -> tuple[bool, str]:
        """
        Add a track to the queue and start playing if nothing is playing.

        Args:
            guild_id: Guild ID
            url: URL to audio source
            requester_id: Discord user ID who requested
            channel_id: Text channel ID for playback announcements
            play_next: Insert at the front of the queue instead of the back

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
                duration=duration,
                channel_id=channel_id
            )

            # Initialize queue for guild if doesn't exist
            if guild_id not in self.queues:
                self.queues[guild_id] = deque()

            if play_next:
                self.queues[guild_id].appendleft(track)
            else:
                self.queues[guild_id].append(track)
            logger.info(f"Added to queue in guild {guild_id}: {title}")

            # If nothing is playing, start playing
            if not voice_client.is_playing() and not voice_client.is_paused():
                await self._play_next(guild_id)
                return True, f"now playing: {title}"
            elif play_next:
                return True, f"up next: {title}"
            else:
                queue_position = len(self.queues[guild_id])
                return True, f"added to queue: {title} (position {queue_position})"

        except Exception as e:
            logger.error(f"Failed to add to queue: {e}", exc_info=True)
            return False, f"failed to add to queue: {str(e)}"

    async def add_playlist_to_queue(
        self,
        guild_id: int,
        tracks,
        requester_id: int,
        channel_id: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        Add multiple pre-resolved tracks to the queue at once.

        Unlike add_to_queue(), this does NOT extract info per track up front —
        titles come from the playlist metadata and yt-dlp resolution happens
        lazily in _play_next(), so queueing a large playlist is instant.

        Args:
            guild_id: Guild ID
            tracks: Iterable of playlist_resolver.PlaylistTrack
            requester_id: Discord user ID who requested
            channel_id: Text channel ID for playback announcements

        Returns:
            Tuple of (success: bool, message: str)
        """
        voice_client = self.get_voice_client(guild_id)
        if not voice_client:
            return False, "not connected to voice channel"

        if guild_id not in self.queues:
            self.queues[guild_id] = deque()

        count = 0
        for track in tracks:
            self.queues[guild_id].append(QueuedTrack(
                url=track.query,
                title=track.title,
                requester_id=requester_id,
                channel_id=channel_id
            ))
            count += 1

        if count == 0:
            return False, "playlist had no playable tracks"

        logger.info(f"Bulk-queued {count} tracks in guild {guild_id}")

        # If nothing is playing, start playing
        if not voice_client.is_playing() and not voice_client.is_paused():
            await self._play_next(guild_id)

        return True, f"queued {count} track(s)"

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

        # Autoplay: feed the queue with a related track when it runs dry
        if (not queue or len(queue) == 0) and self.autoplay.get(guild_id):
            autoplay_track = await asyncio.to_thread(self._pick_autoplay_track, guild_id)
            if autoplay_track:
                if guild_id not in self.queues:
                    self.queues[guild_id] = deque()
                self.queues[guild_id].append(autoplay_track)
                queue = self.queues[guild_id]

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

                # Search queries (ytsearch1:) return a results wrapper
                if 'entries' in info:
                    entries = [e for e in info['entries'] if e]
                    if not entries:
                        raise RuntimeError(f"no search results for: {track.title}")
                    info = entries[0]

                audio_url = info['url']

            # Create audio source, wrapped for per-guild volume control
            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
                volume=self.get_volume(guild_id)
            )

            # Store event loop reference if not already stored
            if not self.loop:
                self.loop = asyncio.get_running_loop()

            track.started_at = time.time()
            if track.duration is None:
                track.duration = info.get('duration')

            # Remember what played, for autoplay seeding and repeat avoidance
            self._last_track[guild_id] = track
            video_id = info.get('id')
            if video_id:
                self._last_video_id[guild_id] = video_id
                if guild_id not in self._recent_video_ids:
                    self._recent_video_ids[guild_id] = deque(maxlen=RECENT_TRACK_MEMORY)
                self._recent_video_ids[guild_id].append(video_id)

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
            await self._announce(track.channel_id, f"couldn't play **{track.title}**, skipping")
            # Try to play next track if this one failed
            return await self._play_next(guild_id)

    async def _announce(self, channel_id: Optional[int], text: str) -> None:
        """Send a playback announcement to a text channel (best effort)."""
        if not self.client or not channel_id:
            return
        try:
            channel = self.client.get_channel(channel_id)
            if channel:
                await channel.send(text)
        except Exception as e:
            logger.warning(f"Failed to send announcement to channel {channel_id}: {e}")

    def _pick_autoplay_track(self, guild_id: int) -> Optional[QueuedTrack]:
        """
        Pick a related track via the YouTube mix for the last played video.

        NOTE: Blocking (network); call from a thread.
        """
        seed_id = self._last_video_id.get(guild_id)
        last_track = self._last_track.get(guild_id)
        if not seed_id or not last_track:
            return None

        mix_url = f"https://www.youtube.com/watch?v={seed_id}&list=RD{seed_id}"
        try:
            with yt_dlp.YoutubeDL(YDL_FLAT_OPTIONS) as ydl:
                info = ydl.extract_info(mix_url, download=False)
        except Exception as e:
            logger.warning(f"Autoplay mix lookup failed for {seed_id}: {e}")
            return None

        recent = self._recent_video_ids.get(guild_id) or ()
        for entry in info.get('entries') or []:
            if not entry:
                continue
            video_id = entry.get('id')
            if not video_id or video_id == seed_id or video_id in recent:
                continue
            url = entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"
            title = entry.get('title') or 'Unknown'
            logger.info(f"Autoplay picked for guild {guild_id}: {title}")
            return QueuedTrack(
                url=url,
                title=f"{title} (autoplay)",
                requester_id=last_track.requester_id,
                duration=entry.get('duration'),
                channel_id=last_track.channel_id
            )

        logger.info(f"Autoplay found no fresh tracks for guild {guild_id}")
        return None

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
            # Stop current playback if any (flagged so the finished-callback
            # doesn't also advance the queue underneath us)
            if voice_client.is_playing():
                self._stopped.add(guild_id)
                voice_client.stop()

            # Extract audio info with yt-dlp
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                logger.info(f"Extracting audio info from: {url}")
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'Unknown')

            # Create audio source
            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
                volume=self.get_volume(guild_id)
            )

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

        track = self.now_playing.get(guild_id)
        was_skipped = guild_id in self._skipped
        was_stopped = guild_id in self._stopped
        self._skipped.discard(guild_id)
        self._stopped.discard(guild_id)

        # stop() halts the queue entirely: put the interrupted track back at
        # the front so a later play/start resumes from it, and don't advance
        if was_stopped:
            if track is not None and not error:
                self.queues.setdefault(guild_id, deque()).appendleft(track)
            self.now_playing[guild_id] = None
            logger.info(f"Playback stopped in guild {guild_id}, queue halted")
            return

        # Loop modes: re-queue the finished track
        mode = self.loop_modes.get(guild_id, 'off')
        if track is not None and not error:
            if mode == 'track' and not was_skipped:
                self.queues.setdefault(guild_id, deque()).appendleft(track)
            elif mode == 'queue':
                self.queues.setdefault(guild_id, deque()).append(track)

        # Clear current track
        self.now_playing[guild_id] = None

        # Play next track if available
        if self.loop:
            # Schedule _play_next() to run in the event loop
            asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.loop)
        else:
            logger.error(f"No event loop reference, cannot auto-play next track in guild {guild_id}")

    def skip(self, guild_id: int) -> Optional[str]:
        """
        Skip the currently playing track (bypasses loop-track re-queueing).

        Args:
            guild_id: Guild ID

        Returns:
            Title of the skipped track, or None if nothing was playing
        """
        voice_client = self.get_voice_client(guild_id)
        if not voice_client or not (voice_client.is_playing() or voice_client.is_paused()):
            return None

        track = self.now_playing.get(guild_id)
        title = track.title if track else "current track"

        self._skipped.add(guild_id)
        voice_client.stop()
        return title

    def remove_from_queue(self, guild_id: int, position: int) -> Optional[QueuedTrack]:
        """
        Remove a track from the queue by its 1-based position.

        Args:
            guild_id: Guild ID
            position: 1-based queue position (as shown by >queue)

        Returns:
            The removed track, or None if position is invalid
        """
        queue = self.queues.get(guild_id)
        if not queue or not (1 <= position <= len(queue)):
            return None

        tracks = list(queue)
        removed = tracks.pop(position - 1)
        queue.clear()
        queue.extend(tracks)

        logger.info(f"Removed from queue in guild {guild_id}: {removed.title}")
        return removed

    def move_in_queue(self, guild_id: int, from_pos: int, to_pos: int) -> Optional[QueuedTrack]:
        """
        Move a track from one 1-based queue position to another.

        Args:
            guild_id: Guild ID
            from_pos: Current 1-based position
            to_pos: Target 1-based position

        Returns:
            The moved track, or None if either position is invalid
        """
        queue = self.queues.get(guild_id)
        if not queue:
            return None
        size = len(queue)
        if not (1 <= from_pos <= size and 1 <= to_pos <= size):
            return None

        tracks = list(queue)
        track = tracks.pop(from_pos - 1)
        tracks.insert(to_pos - 1, track)
        queue.clear()
        queue.extend(tracks)

        logger.info(f"Moved {track.title} from {from_pos} to {to_pos} in guild {guild_id}")
        return track

    def shuffle_queue(self, guild_id: int) -> int:
        """
        Shuffle the queued tracks (does not affect the currently playing track).

        Args:
            guild_id: Guild ID

        Returns:
            Number of tracks in the queue after shuffling
        """
        queue = self.queues.get(guild_id)
        if not queue:
            return 0

        tracks = list(queue)
        random.shuffle(tracks)
        queue.clear()
        queue.extend(tracks)

        logger.info(f"Shuffled {len(tracks)} queued tracks in guild {guild_id}")
        return len(tracks)

    def set_loop_mode(self, guild_id: int, mode: str) -> None:
        """Set loop mode for a guild ('off', 'track', or 'queue')."""
        if mode not in LOOP_MODES:
            raise ValueError(f"invalid loop mode: {mode}")
        self.loop_modes[guild_id] = mode

    def get_loop_mode(self, guild_id: int) -> str:
        """Get loop mode for a guild."""
        return self.loop_modes.get(guild_id, 'off')

    def set_autoplay(self, guild_id: int, enabled: bool) -> None:
        """Enable or disable autoplay for a guild."""
        self.autoplay[guild_id] = enabled

    def get_autoplay(self, guild_id: int) -> bool:
        """Whether autoplay is enabled for a guild."""
        return self.autoplay.get(guild_id, False)

    def set_volume(self, guild_id: int, volume: float) -> None:
        """
        Set playback volume for a guild (1.0 = 100%), applied immediately
        to the current track if one is playing.
        """
        self.volumes[guild_id] = volume
        voice_client = self.get_voice_client(guild_id)
        source = getattr(voice_client, 'source', None)
        if source is not None and hasattr(source, 'volume'):
            source.volume = volume

    def get_volume(self, guild_id: int) -> float:
        """Get playback volume for a guild (default 1.0)."""
        return self.volumes.get(guild_id, 1.0)

    def check_idle(self, idle_timeout: float, now: Optional[float] = None) -> List[int]:
        """
        Find guilds whose voice connection has been idle for too long.

        A guild counts as idle when nothing is playing or paused, or when
        no non-bot members remain in the voice channel.

        Args:
            idle_timeout: Seconds of continuous idleness before disconnect
            now: Current unix timestamp (defaults to time.time(); injectable for tests)

        Returns:
            List of guild IDs that should be disconnected
        """
        if now is None:
            now = time.time()

        to_disconnect = []
        for guild_id, voice_client in list(self.voice_clients.items()):
            active = voice_client.is_playing() or voice_client.is_paused()
            members = getattr(getattr(voice_client, 'channel', None), 'members', None) or []
            alone = not any(not getattr(m, 'bot', False) for m in members)

            if active and not alone:
                self._idle_since.pop(guild_id, None)
                continue

            idle_start = self._idle_since.setdefault(guild_id, now)
            if now - idle_start >= idle_timeout:
                to_disconnect.append(guild_id)

        return to_disconnect

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
        """
        Stop playback and halt the queue.

        The interrupted track goes back to the front of the queue, which is
        otherwise left untouched; use start_queue() to pick it back up.
        """
        voice_client = self.get_voice_client(guild_id)
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            self._stopped.add(guild_id)
            voice_client.stop()
            return True
        return False

    async def start_queue(self, guild_id: int) -> bool:
        """
        Start playing the queue if connected and nothing is playing
        (e.g. after stop()).

        Returns:
            True if a track started playing
        """
        voice_client = self.get_voice_client(guild_id)
        if not voice_client or voice_client.is_playing() or voice_client.is_paused():
            return False
        return await self._play_next(guild_id)
