"""Main message handling orchestration."""

import logging
from typing import Optional, List
from message_parser import parse_message, ParsedMessage
from context_manager import ThreadContextManager
from command_router import dispatch, CommandResult
from model_bridge import query_llm

logger = logging.getLogger(__name__)


class CommandContext:
    """Simple context object for command router."""

    def __init__(self, message, bot_user_id: int, role_ids: List[int], reminder_manager=None):
        self.content = message.content
        self.anna_user_id = bot_user_id
        self.role_ids = role_ids
        self.message = message
        self.reminder_manager = reminder_manager


class MessageHandler:
    """Handles incoming Discord messages and coordinates responses."""

    def __init__(self, bot_user_id: int, bot_role_ids: List[int], reminder_manager=None):
        """
        Initialize the message handler.

        Args:
            bot_user_id: The bot's Discord user ID
            bot_role_ids: List of role IDs that trigger the bot
            reminder_manager: Optional ReminderManager instance
        """
        self.bot_user_id = bot_user_id
        self.bot_role_ids = bot_role_ids
        self.reminder_manager = reminder_manager
        self.context_manager = ThreadContextManager()
        logger.info("MessageHandler initialized")

    async def handle_message(self, message) -> Optional[str]:
        """
        Main entry point for processing Discord messages.

        Args:
            message: Discord message object

        Returns:
            Response text or None if no response needed
        """
        # Parse message
        referenced_author_id = None
        if message.reference and message.reference.resolved:
            referenced_author_id = message.reference.resolved.author.id

        parsed = parse_message(
            message.content,
            self.bot_user_id,
            self.bot_role_ids,
            referenced_author_id
        )

        logger.debug(f"Parsed message: mentioned={parsed.is_bot_mentioned}, "
                    f"command={parsed.is_command}, special={parsed.is_special_command}")

        # Handle special commands (reset context)
        if parsed.is_special_command:
            return await self._handle_special_command(parsed, message)

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

        # Try command routing first (if message has > prefix)
        if parsed.is_command:
            logger.info(f"Command detected: {parsed.clean_prompt}")
            try:
                ctx = CommandContext(message, self.bot_user_id, self.bot_role_ids, self.reminder_manager)
                result = await dispatch(ctx)

                if result.handled:
                    logger.info(f"Command handled successfully")
                    return result.text
                else:
                    logger.debug("Command not handled, falling through to AI")
            except Exception as e:
                logger.error(f"Command dispatch failed: {e}", exc_info=True)
                return f"command failed: {e}"

        # Fall back to AI response
        return await self._handle_ai_response(message, parsed)

    async def _handle_special_command(self, parsed: ParsedMessage, message) -> str:
        """Handle special commands like context reset."""
        if parsed.special_command_type == "reset_context":
            logger.info("Clearing all thread contexts")
            self.context_manager.clear_context()
            return "i've deleted myself. i got no chance to win."
        return "unknown special command"

    async def _handle_ai_response(self, message, parsed: ParsedMessage) -> str:
        """Query LLM and return response."""
        thread_id = str(message.channel.id)

        # Add user message to context
        self.context_manager.add_message(thread_id, "user", parsed.clean_prompt)
        logger.debug(f"Added user message to thread {thread_id}")

        # Get full context
        context = self.context_manager.get_context(thread_id)
        logger.info(f"Querying LLM with {len(context)} messages of context")

        # Query LLM
        try:
            response = query_llm(context)
        except Exception as e:
            logger.error(f"LLM query failed: {e}", exc_info=True)
            return "brain exploded mid-thought, try again later."

        if not response:
            logger.warning("LLM returned empty response")
            return "brain exploded mid-thought, try again later."

        # Add assistant response to context
        self.context_manager.add_message(thread_id, "assistant", response)
        logger.debug(f"Added assistant response to thread {thread_id}")

        return response
