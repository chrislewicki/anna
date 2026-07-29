"""List pending reminders command."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from utils import format_duration_long

if TYPE_CHECKING:
    from message_handler import CommandContext


def user_reminders_sorted(ctx: 'CommandContext'):
    """The invoking user's pending reminders, soonest first (shared with >cancel)."""
    pending = ctx.reminder_manager.get_user_reminders(ctx.message.author.id)
    return sorted(pending, key=lambda r: r.due_time)


async def reminders(ctx: 'CommandContext', args: str) -> str:
    """
    List your pending reminders.

    Usage: @Anna >reminders

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Numbered list of pending reminders
    """
    pending = user_reminders_sorted(ctx)
    if not pending:
        return "you have no pending reminders"

    now = datetime.now(timezone.utc).timestamp()
    lines = ["**your reminders:**"]
    for i, reminder in enumerate(pending, 1):
        remaining = format_duration_long(max(0, int(reminder.due_time - now)))
        lines.append(f"{i}. in {remaining}: {reminder.message}")
    lines.append("cancel one with `>cancel <number>`")
    return "\n".join(lines)
