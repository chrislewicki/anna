"""Stop playback command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def stop(ctx: 'CommandContext', args: str) -> str:
    """
    Stop playback and halt the queue.

    Usage: @Anna stop

    The queue is kept (including the stopped track) — restart it with
    `@Anna play`, or wipe it with `@Anna clear`.

    Args:
        ctx: Command context
        args: Unused

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id

    # Count before stopping: the playback callback re-queues the stopped
    # track asynchronously, so the queue length right after stop() is racy
    queue = ctx.music_manager.queues.get(guild_id)
    queued = (len(queue) if queue else 0)
    if ctx.music_manager.now_playing.get(guild_id):
        queued += 1

    if not ctx.music_manager.stop(guild_id):
        return "nothing is playing"

    return f"stopped playback — {queued} track(s) still queued, `@Anna play` to resume"
