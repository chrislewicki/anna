"""Autoplay (radio mode) command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext


async def autoplay(ctx: 'CommandContext', args: str) -> str:
    """
    Toggle autoplay: when the queue runs out, keep playing related tracks.

    Usage: @Anna >autoplay [on|off]

    With no argument, toggles the current setting. Related tracks come
    from the YouTube mix for the last played track.

    Args:
        ctx: Command context
        args: "on", "off", or empty to toggle

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id
    arg = args.strip().lower()

    if arg == 'on':
        enabled = True
    elif arg == 'off':
        enabled = False
    elif not arg:
        enabled = not ctx.music_manager.get_autoplay(guild_id)
    else:
        return "usage: `>autoplay [on|off]`"

    ctx.music_manager.set_autoplay(guild_id, enabled)
    if enabled:
        return "autoplay **on** — i'll keep the music going when the queue runs out"
    return "autoplay **off**"
