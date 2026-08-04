"""Persistence for server-saved playlists (the >saveq / >loadq commands)."""

import json
import logging
from typing import List, Optional
from config import PLAYLISTS_FILE
from utils import atomic_json_save

logger = logging.getLogger(__name__)


class PlaylistStore:
    """Stores named playlists per guild in a JSON file.

    Data shape: {guild_id (str): {name_lower: {"name": str, "tracks": [{"url", "title"}]}}}
    """

    def __init__(self, playlists_file: str = PLAYLISTS_FILE):
        self.playlists_file = playlists_file
        self.data: dict = {}
        self.load()

    def load(self) -> None:
        """Load playlists from disk."""
        try:
            with open(self.playlists_file, "r") as f:
                self.data = json.load(f)
            logger.info(f"Loaded saved playlists from {self.playlists_file}")
        except FileNotFoundError:
            self.data = {}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse playlists file: {e}. Starting fresh.")
            self.data = {}
        except Exception as e:
            logger.error(f"Error loading playlists: {e}", exc_info=True)
            self.data = {}

    def save(self) -> None:
        """Save playlists to disk atomically."""
        atomic_json_save(self.data, self.playlists_file)

    def save_playlist(self, guild_id: int, name: str, tracks: List[dict]) -> None:
        """
        Save (or overwrite) a named playlist for a guild.

        Args:
            guild_id: Guild ID
            name: Display name (lookup is case-insensitive)
            tracks: List of {"url": str, "title": str} dicts, in order
        """
        guild = self.data.setdefault(str(guild_id), {})
        guild[name.lower()] = {"name": name, "tracks": tracks}
        self.save()
        logger.info(f"Saved playlist '{name}' ({len(tracks)} tracks) for guild {guild_id}")

    def get_playlist(self, guild_id: int, name: str) -> Optional[dict]:
        """Get a saved playlist by name, or None."""
        return self.data.get(str(guild_id), {}).get(name.lower())

    def delete_playlist(self, guild_id: int, name: str) -> bool:
        """Delete a saved playlist. Returns True if it existed."""
        guild = self.data.get(str(guild_id), {})
        if name.lower() in guild:
            del guild[name.lower()]
            self.save()
            logger.info(f"Deleted playlist '{name}' for guild {guild_id}")
            return True
        return False

    def list_playlists(self, guild_id: int) -> List[dict]:
        """List saved playlists for a guild, sorted by name."""
        guild = self.data.get(str(guild_id), {})
        return sorted(guild.values(), key=lambda p: p["name"].lower())
