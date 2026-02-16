"""Message parsing logic for Discord messages."""

from dataclasses import dataclass
from typing import Optional, List
from config import SPECIAL_RESET_COMMANDS, PASSIVE_MENTION_TRIGGERS


@dataclass
class ParsedMessage:
    """Represents a parsed Discord message with extracted metadata."""

    is_bot_mentioned: bool
    is_reply_to_bot: bool
    is_passive_mention: bool
    is_special_command: bool
    special_command_type: Optional[str]
    is_command: bool
    clean_prompt: str
    original_content: str


def parse_message(
    content: str,
    bot_user_id: int,
    bot_role_ids: List[int],
    referenced_message_author_id: Optional[int] = None
) -> ParsedMessage:
    """
    Parse a Discord message and extract all relevant metadata.

    Args:
        content: The message content
        bot_user_id: The bot's Discord user ID
        bot_role_ids: List of role IDs that trigger the bot
        referenced_message_author_id: Author ID if this is a reply, None otherwise

    Returns:
        ParsedMessage with all extracted metadata
    """
    original_content = content
    is_reply_to_bot = referenced_message_author_id == bot_user_id if referenced_message_author_id else False

    # Check for special commands (context reset)
    is_special_command = content.lower().strip() in SPECIAL_RESET_COMMANDS
    special_command_type = "reset_context" if is_special_command else None

    # Check for direct mentions (user or role)
    is_user_mentioned = f"<@{bot_user_id}>" in content or f"<@!{bot_user_id}>" in content
    is_role_mentioned = any(f"<@&{role_id}>" in content for role_id in bot_role_ids)
    is_bot_mentioned = is_user_mentioned or is_role_mentioned or is_reply_to_bot

    # Check for passive mentions ("anna" in conversation)
    is_passive_mention = any(trigger in content.lower() for trigger in PASSIVE_MENTION_TRIGGERS)

    # Extract clean prompt (remove mentions)
    clean_prompt = content
    clean_prompt = clean_prompt.replace(f"<@{bot_user_id}>", "")
    clean_prompt = clean_prompt.replace(f"<@!{bot_user_id}>", "")
    for role_id in bot_role_ids:
        clean_prompt = clean_prompt.replace(f"<@&{role_id}>", "")
    clean_prompt = clean_prompt.strip()

    # Check if this is a command (has > after mention)
    is_command = is_bot_mentioned and clean_prompt.startswith(">")

    return ParsedMessage(
        is_bot_mentioned=is_bot_mentioned,
        is_reply_to_bot=is_reply_to_bot,
        is_passive_mention=is_passive_mention,
        is_special_command=is_special_command,
        special_command_type=special_command_type,
        is_command=is_command,
        clean_prompt=clean_prompt,
        original_content=original_content
    )
