"""Loop mode command."""

from typing import TYPE_CHECKING
from music_manager import LOOP_MODES

if TYPE_CHECKING:
    from message_handler import CommandContext


async def loop(ctx: 'CommandContext', args: str) -> str:
    """
    Set or show the loop mode.

    Usage: @Anna loop [track|queue|off]
        track - repeat the current track
        queue - re-queue each track after it plays
        off   - play through the queue once (default)

    With no argument, shows the current mode. Skip always moves on,
    even in track mode.

    Args:
        ctx: Command context
        args: Loop mode, or empty to show current

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id
    mode = args.strip().lower()

    if not mode:
        return f"loop mode: **{ctx.music_manager.get_loop_mode(guild_id)}**"

    if mode not in LOOP_MODES:
        return "usage: `@Anna loop track|queue|off`"

    ctx.music_manager.set_loop_mode(guild_id, mode)
    if mode == 'off':
        return "loop off"
    return f"looping the {mode}"
