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
import os

# Provider selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "digitalocean")
"""LLM provider to use. Options: digitalocean, ollama-local, ollama-tailscale"""

# Shared LLM settings
LLM_TIMEOUT_SECONDS = 20
"""Timeout for LLM API requests."""

LLM_TEMPERATURE = 0.7
"""LLM temperature (creativity) setting. Range: 0.0-1.0."""

LLM_MAX_TOKENS = 8124
"""Maximum tokens in LLM response."""

LLM_SYSTEM_PROMPT = os.getenv("LLM_SYSTEM_PROMPT", "")
"""Default system prompt for all providers. Can be overridden per provider."""

# DigitalOcean GenAI provider configuration
DIGITALOCEAN_MODEL_URL = os.getenv(
    "DIGITALOCEAN_MODEL_URL",
    "https://ppjmbaf3sh6p5tx2iaz53gmr.agents.do-ai.run/api/v1/chat/completions"
)
"""DigitalOcean GenAI Platform endpoint URL."""

DIGITALOCEAN_AUTH_TOKEN = os.getenv("DIGITALOCEAN_AUTH_TOKEN", os.getenv("AUTH_TOKEN", ""))
"""DigitalOcean API authentication token. Falls back to AUTH_TOKEN for backward compatibility."""

DIGITALOCEAN_MODEL = os.getenv("DIGITALOCEAN_MODEL", "mistral")
"""Model name to use with DigitalOcean GenAI."""

DIGITALOCEAN_SYSTEM_PROMPT = os.getenv("DIGITALOCEAN_SYSTEM_PROMPT", "")
"""System prompt for DigitalOcean provider. Overrides LLM_SYSTEM_PROMPT if set."""

# Ollama local provider configuration
OLLAMA_LOCAL_URL = os.getenv("OLLAMA_LOCAL_URL", "http://localhost:11434")
"""Local ollama instance URL. Requires network_mode: host in docker-compose.yml"""

OLLAMA_LOCAL_MODEL = os.getenv("OLLAMA_LOCAL_MODEL", "tinyllama")
"""Model name to use with local ollama."""

OLLAMA_LOCAL_SYSTEM_PROMPT = os.getenv(
    "OLLAMA_LOCAL_SYSTEM_PROMPT",
    "You are Anna, a helpful Discord bot. Respond concisely and directly to questions."
)
"""System prompt for local ollama provider. Overrides LLM_SYSTEM_PROMPT if set."""

# Ollama Tailscale provider configuration
OLLAMA_TAILSCALE_URL = os.getenv("OLLAMA_TAILSCALE_URL", "")
"""Tailscale ollama instance URL (e.g., http://hostname.tail-scale.ts.net:11434)"""

OLLAMA_TAILSCALE_MODEL = os.getenv("OLLAMA_TAILSCALE_MODEL", "mistral")
"""Model name to use with Tailscale ollama."""

OLLAMA_TAILSCALE_SYSTEM_PROMPT = os.getenv("OLLAMA_TAILSCALE_SYSTEM_PROMPT", "")
"""System prompt for Tailscale ollama provider. Overrides LLM_SYSTEM_PROMPT if set."""

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
