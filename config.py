"""Configuration constants for Anna Discord bot."""

# Discord configuration
ANNA_ROLE_IDS = [1359662416165732464]
"""Discord role IDs that trigger the bot when mentioned."""

# Background task intervals (seconds)
REMINDER_CHECK_INTERVAL_SECONDS = 10
"""How often to check for due reminders."""

# Reminder settings
REMINDERS_FILE = "reminders.json"
"""File path for persisting reminders."""

REMINDER_MIN_TIME_SECONDS = 10
"""Minimum allowed reminder time (10 seconds)."""

REMINDER_MAX_TIME_SECONDS = 365 * 86400  # 1 year
"""Maximum allowed reminder time (1 year)."""

# Triggers for passive mentions (just react, don't respond)
PASSIVE_MENTION_TRIGGERS = [
    " anna ",
    " anna,",
    " anna.",
    " anna!",
    " anna;",
    " anna?"
]
"""Text patterns that trigger a reaction emoji but no response."""

# Speed test settings
SPEEDTEST_TIMEOUT_SECONDS = 60
"""Maximum time allowed for speed test (safety net)."""
