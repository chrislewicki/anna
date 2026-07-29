"""Volume control command."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext

MAX_VOLUME_PERCENT = 200


async def volume(ctx: 'CommandContext', args: str) -> str:
    """
    Set or show the playback volume.

    Usage: @Anna >volume [0-200]
    Examples:
        @Anna >volume       (show current volume)
        @Anna >volume 50    (half volume)
        @Anna >volume 100   (normal)

    Applies immediately to the current track and persists for future tracks.

    Args:
        ctx: Command context
        args: Volume percentage, or empty to show current

    Returns:
        Status message
    """
    guild_id = ctx.message.guild.id

    if not args.strip():
        current = round(ctx.music_manager.get_volume(guild_id) * 100)
        return f"volume: **{current}%**"

    try:
        percent = int(args.strip().rstrip('%'))
    except ValueError:
        return "usage: `>volume <0-200>`"

    if not (0 <= percent <= MAX_VOLUME_PERCENT):
        return f"volume must be between 0 and {MAX_VOLUME_PERCENT}"

    ctx.music_manager.set_volume(guild_id, percent / 100)
    return f"volume set to **{percent}%**"
