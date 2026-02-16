"""Anna Discord Bot - Main entry point."""

import discord
import logging
import asyncio
import signal
from dotenv import load_dotenv
import os
from message_handler import MessageHandler
from reminder_manager import ReminderManager
from music_manager import MusicManager
from config import ANNA_ROLE_IDS, REMINDER_CHECK_INTERVAL_SECONDS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Set up Discord client
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

client = discord.Client(intents=intents)
handler = None  # Will be initialized in on_ready
reminder_manager = None  # Will be initialized in on_ready
music_manager = None  # Will be initialized in on_ready


def validate_environment():
    """
    Validate that required environment variables are set.

    Raises:
        ValueError: If any required environment variables are missing
    """
    required = {
        "DISCORD_TOKEN": "Discord bot token",
        "AUTH_TOKEN": "LLM API authentication token"
    }

    missing = []
    for var, description in required.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")

    if missing:
        error_msg = "Missing required environment variables:\n" + "\n".join(f"  - {m}" for m in missing)
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Environment validation passed")


def handle_shutdown(signum, frame):
    """
    Handle shutdown signals gracefully.

    Saves bot state before exiting to prevent data loss.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down gracefully...")

    # Save state before shutting down
    if reminder_manager:
        logger.info("Saving reminders...")
        reminder_manager.save()

    if handler and handler.context_manager:
        logger.info("Saving context...")
        handler.context_manager.save()

    logger.info("Shutdown complete")
    client.loop.stop()


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


@client.event
async def on_ready():
    """Called when bot successfully connects to Discord."""
    global handler, reminder_manager, music_manager

    # Prevent re-initialization on reconnection
    if handler is not None:
        logger.info("Bot already initialized, skipping re-initialization")
        return

    # Initialize managers (order matters - reminder_manager must exist first)
    reminder_manager = ReminderManager()
    music_manager = MusicManager()
    handler = MessageHandler(client.user.id, ANNA_ROLE_IDS, reminder_manager, music_manager)
    logger.info(f"Logged in as {client.user}")

    # Start reminder background task
    asyncio.create_task(check_reminders())
    logger.info("Reminder checker started")


@client.event
async def on_message(message):
    """Called when a message is received."""
    # Ignore own messages
    if message.author == client.user:
        return

    # Safety check: ensure handler is initialized
    if handler is None:
        logger.warning("Handler not yet initialized, ignoring message")
        return

    try:
        response = await handler.handle_message(message)
        if response:
            await message.reply(response)
    except Exception as e:
        logger.error(f"Failed to handle message: {e}", exc_info=True)
        try:
            await message.reply("something broke. oops.")
        except Exception as reply_error:
            logger.error(f"Failed to send error message to user: {reply_error}")


@client.event
async def on_close():
    """Called when bot disconnects from Discord."""
    logger.info("Bot disconnecting, saving state...")
    if reminder_manager:
        reminder_manager.save()
    if handler:
        handler.context_manager.save()


async def check_reminders():
    """Background task that checks for due reminders periodically."""
    await client.wait_until_ready()  # Wait for client to be fully ready
    logger.info("Reminder background task started")

    while not client.is_closed():
        try:
            # Reload reminders from disk to pick up any new ones
            reminder_manager.load()

            # Get all due reminders
            due_reminders = reminder_manager.get_due_reminders()

            for reminder in due_reminders:
                try:
                    # Get the channel where reminder should be sent
                    channel = client.get_channel(reminder.channel_id)

                    if channel:
                        # Send reminder with user mention
                        await channel.send(
                            f"<@{reminder.user_id}> reminder: {reminder.message}"
                        )
                        logger.info(f"Sent reminder {reminder.id} to channel {reminder.channel_id}")
                    else:
                        logger.warning(
                            f"Channel {reminder.channel_id} not found for reminder {reminder.id}"
                        )

                    # Remove the completed reminder
                    reminder_manager.remove_reminder(reminder.id)

                except Exception as e:
                    logger.error(f"Failed to send reminder {reminder.id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in reminder checker loop: {e}", exc_info=True)

        # Check every N seconds (configurable)
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)


# Run the bot
if __name__ == "__main__":
    logger.info("Starting Anna Discord Bot...")
    validate_environment()
    client.run(DISCORD_TOKEN)
