"""Reminder management and persistence."""

import json
import os
import logging
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List, Optional
from config import REMINDERS_FILE
from utils import atomic_json_save

logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    """Represents a pending reminder."""

    id: str
    user_id: int
    channel_id: int
    message: str
    due_time: float  # Unix timestamp
    created_at: float  # Unix timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'Reminder':
        """Create Reminder from dictionary."""
        return Reminder(**data)


class ReminderManager:
    """Manages reminder storage and retrieval."""

    def __init__(self, reminders_file: str = REMINDERS_FILE):
        """
        Initialize the reminder manager.

        Args:
            reminders_file: Path to the JSON file for persisting reminders
        """
        self.reminders_file = reminders_file
        self.reminders: List[Reminder] = []
        self.load()

    def load(self) -> None:
        """Load reminders from disk."""
        try:
            with open(self.reminders_file, "r") as f:
                data = json.load(f)
                self.reminders = [Reminder.from_dict(r) for r in data]
                logger.info(f"Loaded {len(self.reminders)} reminders from {self.reminders_file}")
        except FileNotFoundError:
            logger.info(f"No saved reminders found at {self.reminders_file}. Starting fresh.")
            self.reminders = []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse reminders file: {e}. Starting fresh.")
            self.reminders = []
        except Exception as e:
            logger.error(f"Error loading reminders: {e}", exc_info=True)
            self.reminders = []

    def save(self) -> None:
        """Save reminders to disk atomically."""
        data = [r.to_dict() for r in self.reminders]
        atomic_json_save(data, self.reminders_file)
        logger.debug(f"Saved {len(self.reminders)} reminders to {self.reminders_file}")

    def add_reminder(
        self,
        user_id: int,
        channel_id: int,
        message: str,
        due_time: float
    ) -> Reminder:
        """
        Create and save a new reminder.

        Args:
            user_id: Discord user ID to mention
            channel_id: Discord channel ID where to send reminder
            message: Reminder message text
            due_time: Unix timestamp when reminder is due

        Returns:
            The created Reminder object
        """
        reminder = Reminder(
            id=str(uuid.uuid4()),
            user_id=user_id,
            channel_id=channel_id,
            message=message,
            due_time=due_time,
            created_at=datetime.now(timezone.utc).timestamp()
        )

        self.reminders.append(reminder)
        self.save()

        logger.info(f"Created reminder {reminder.id} for user {user_id} due at {due_time}")
        return reminder

    def get_due_reminders(self) -> List[Reminder]:
        """
        Get all reminders that are due now.

        Returns:
            List of reminders whose due_time is <= current time
        """
        now = datetime.now(timezone.utc).timestamp()
        due = [r for r in self.reminders if r.due_time <= now]

        if due:
            logger.debug(f"Found {len(due)} due reminders")

        return due

    def remove_reminder(self, reminder_id: str) -> None:
        """
        Remove a reminder by ID.

        Args:
            reminder_id: The reminder ID to remove
        """
        original_count = len(self.reminders)
        self.reminders = [r for r in self.reminders if r.id != reminder_id]

        if len(self.reminders) < original_count:
            self.save()
            logger.debug(f"Removed reminder {reminder_id}")
        else:
            logger.warning(f"Reminder {reminder_id} not found for removal")

    def get_user_reminders(self, user_id: int) -> List[Reminder]:
        """
        Get all pending reminders for a specific user.

        Args:
            user_id: Discord user ID

        Returns:
            List of pending reminders for the user
        """
        return [r for r in self.reminders if r.user_id == user_id]

    def get_reminder_count(self) -> int:
        """Get total number of pending reminders."""
        return len(self.reminders)
