"""Configuration constants for Anna Discord bot.

This module centralizes all configuration values, making it easy to adjust
bot behavior without searching through multiple files.
"""

# Discord configuration
ANNA_ROLE_IDS = [1359662416165732464]
"""Discord role IDs that trigger the bot when mentioned."""

# Background task intervals (seconds)
REMINDER_CHECK_INTERVAL_SECONDS = 10
"""How often to check for due reminders."""

# Context management
CONTEXT_MAX_MESSAGES = 12
"""Maximum number of messages to keep in conversation history per thread."""

CONTEXT_FILE = "thread_context.json"
"""File path for persisting conversation context."""

# Reminder settings
REMINDERS_FILE = "reminders.json"
"""File path for persisting reminders."""

REMINDER_MIN_TIME_SECONDS = 10
"""Minimum allowed reminder time (10 seconds)."""

REMINDER_MAX_TIME_SECONDS = 365 * 86400  # 1 year
"""Maximum allowed reminder time (1 year)."""

# LLM/Model settings
LLM_TIMEOUT_SECONDS = 20
"""Timeout for LLM API requests."""

LLM_TEMPERATURE = 0.7
"""LLM temperature (creativity) setting. Range: 0.0-1.0."""

LLM_MAX_TOKENS = 8124
"""Maximum tokens in LLM response."""

# Special commands that trigger context reset
SPECIAL_RESET_COMMANDS = [
    "anna, delete yourself",
    "anna, reset context",
    "anna, forget everything"
]
"""Commands that clear conversation history."""

# Triggers for passive mentions (just react, don't respond)
PASSIVE_MENTION_TRIGGERS = [
    " anna ",
    " anna,",
    " anna.",
    " anna!",
    " anna;",
    " anna?"
]
"""Text patterns that trigger a reaction emoji but no AI response."""

# Speed test settings
SPEEDTEST_TIMEOUT_SECONDS = 60
"""Maximum time allowed for speed test (safety net)."""
