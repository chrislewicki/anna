"""Cancel reminder command."""

from typing import TYPE_CHECKING
from .reminders import user_reminders_sorted

if TYPE_CHECKING:
    from message_handler import CommandContext


async def cancel(ctx: 'CommandContext', args: str) -> str:
    """
    Cancel one of your pending reminders.

    Usage: @Anna >cancel <number|all>
    Examples:
        @Anna >cancel 2     (cancel reminder 2 from >reminders)
        @Anna >cancel all   (cancel everything)

    Args:
        ctx: Command context
        args: Reminder number (from >reminders) or "all"

    Returns:
        Status message
    """
    arg = args.strip().lower()
    if not arg:
        return "usage: `>cancel <number|all>` (see numbers with `>reminders`)"

    pending = user_reminders_sorted(ctx)
    if not pending:
        return "you have no pending reminders"

    if arg == 'all':
        for reminder in pending:
            ctx.reminder_manager.remove_reminder(reminder.id)
        return f"cancelled {len(pending)} reminder(s)"

    try:
        number = int(arg)
    except ValueError:
        return "usage: `>cancel <number|all>` (see numbers with `>reminders`)"

    if not (1 <= number <= len(pending)):
        return f"no reminder number {number} — you have {len(pending)} (see `>reminders`)"

    reminder = pending[number - 1]
    ctx.reminder_manager.remove_reminder(reminder.id)
    return f"cancelled reminder: \"{reminder.message}\""
