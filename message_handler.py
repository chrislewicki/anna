"""Main message handling orchestration."""

import logging
from typing import Optional, List
from message_parser import parse_message
from command_router import dispatch, CommandResult

logger = logging.getLogger(__name__)


class CommandContext:
    """Simple context object for command router."""

    def __init__(self, message, bot_user_id: int, role_ids: List[int], reminder_manager=None, music_manager=None):
        self.content = message.content
        self.anna_user_id = bot_user_id
        self.role_ids = role_ids
        self.message = message
        self.reminder_manager = reminder_manager
        self.music_manager = music_manager


class MessageHandler:
    """Handles incoming Discord messages and coordinates responses."""

    def __init__(self, bot_user_id: int, bot_role_ids: List[int], reminder_manager=None, music_manager=None):
        self.bot_user_id = bot_user_id
        self.bot_role_ids = bot_role_ids
        self.reminder_manager = reminder_manager
        self.music_manager = music_manager
        logger.info("MessageHandler initialized")

    async def handle_message(self, message) -> Optional[str]:
        """
        Main entry point for processing Discord messages.

        Args:
            message: Discord message object

        Returns:
            Response text or None if no response needed
        """
        referenced_author_id = None
        if message.reference and message.reference.resolved:
            referenced_author_id = message.reference.resolved.author.id

        parsed = parse_message(
            message.content,
            self.bot_user_id,
            self.bot_role_ids,
            referenced_author_id
        )

        logger.debug(f"Parsed message: mentioned={parsed.is_bot_mentioned}, command={parsed.is_command}")

        # Handle passive mentions (just react)
        if parsed.is_passive_mention and not parsed.is_bot_mentioned:
            logger.debug("Passive mention detected, reacting with 👀")
            try:
                await message.add_reaction("👀")
            except Exception as e:
                logger.warning(f"Failed to add reaction: {e}")
            return None

        # Not mentioned, ignore
        if not parsed.is_bot_mentioned:
            return None

        # Empty mention
        if not parsed.clean_prompt:
            logger.debug("Empty mention detected")
            return "you rang, nerd?"

        # Dispatch to command router
        logger.info(f"Command detected: {parsed.clean_prompt}")
        try:
            ctx = CommandContext(message, self.bot_user_id, self.bot_role_ids, self.reminder_manager, self.music_manager)
            result = await dispatch(ctx)
            return result.text
        except Exception as e:
            logger.error(f"Command dispatch failed: {e}", exc_info=True)
            return f"command failed: {e}"
