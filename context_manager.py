"""Thread context management for conversation history."""

import json
import os
import logging
from typing import List, Dict, Optional
from config import CONTEXT_FILE, CONTEXT_MAX_MESSAGES
from utils import atomic_json_save

logger = logging.getLogger(__name__)


class ThreadContextManager:
    """Manages conversation context/history for Discord threads."""

    def __init__(self, context_file: str = CONTEXT_FILE, max_messages: int = CONTEXT_MAX_MESSAGES):
        """
        Initialize the context manager.

        Args:
            context_file: Path to the JSON file for persisting context
            max_messages: Maximum number of messages to keep per thread
        """
        self.context_file = context_file
        self.max_messages = max_messages
        self.contexts: Dict[str, List[dict]] = {}
        self.dirty = False  # Track if save needed
        self.load()

    def load(self) -> None:
        """Load context from disk."""
        try:
            with open(self.context_file, "r") as f:
                self.contexts = json.load(f)
                logger.info(f"Loaded thread context from {self.context_file}")
        except FileNotFoundError:
            logger.info(f"No saved context found at {self.context_file}. Starting fresh.")
            self.contexts = {}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse context file: {e}. Starting fresh.")
            self.contexts = {}

    def save(self) -> None:
        """Save context to disk atomically."""
        if not self.dirty:
            return  # Skip if nothing changed

        atomic_json_save(self.contexts, self.context_file)
        self.dirty = False
        logger.debug(f"Saved thread context to {self.context_file}")

    def get_context(self, thread_id: str) -> List[dict]:
        """
        Get message history for a thread.

        Args:
            thread_id: The thread/channel ID

        Returns:
            List of messages in OpenAI format [{"role": "user/assistant", "content": "..."}]
        """
        if thread_id not in self.contexts:
            self.contexts[thread_id] = []
        return self.contexts[thread_id]

    def add_message(self, thread_id: str, role: str, content: str) -> None:
        """
        Add a message to thread context and save.

        Args:
            thread_id: The thread/channel ID
            role: Either "user" or "assistant"
            content: The message content
        """
        context = self.get_context(thread_id)
        context.append({"role": role, "content": content})

        # Trim to max size
        if len(context) > self.max_messages:
            self.contexts[thread_id] = context[-self.max_messages:]
            logger.debug(f"Trimmed context for thread {thread_id} to {self.max_messages} messages")

        self.dirty = True

        # Save every 5 messages instead of every message (debounced saves)
        total_messages = sum(len(ctx) for ctx in self.contexts.values())
        if total_messages % 5 == 0:
            self.save()

    def clear_context(self, thread_id: Optional[str] = None) -> None:
        """
        Clear context for one thread or all threads.

        Args:
            thread_id: Thread to clear, or None to clear all threads
        """
        if thread_id:
            if thread_id in self.contexts:
                del self.contexts[thread_id]
                logger.info(f"Cleared context for thread {thread_id}")
        else:
            self.contexts = {}
            logger.info("Cleared all thread contexts")
            try:
                os.remove(self.context_file)
                logger.debug(f"Deleted context file {self.context_file}")
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning(f"Failed to delete context file: {e}")

        self.dirty = True
        self.save()
