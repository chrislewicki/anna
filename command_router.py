import shlex
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CommandResult:
    handled: bool
    text: Optional[str] = None

def _find_anna_mention_span(content: str, anna_user_id: int, role_ids: Optional[list] = None) -> Optional[Tuple[int, int]]:
    needles = [f"<@{anna_user_id}>", f"<@!{anna_user_id}>"]
    if role_ids:
        needles.extend([f"<@&{role_id}>" for role_id in role_ids])
    for n in needles:
        i = content.find(n)
        if i != -1:
            return (i, i + len(n))
    return None

def extract_command_from_mention(content: str, anna_user_id: int, role_ids: Optional[list] = None) -> Tuple[str, str]:
    span = _find_anna_mention_span(content, anna_user_id, role_ids)
    if not span:
        return "", ""
    body = content[span[1]:].lstrip()
    if not body:
        return "", ""
    try:
        tokens = shlex.split(body)
    except ValueError:
        tokens = body.split()
    cmd = tokens[0].lower()
    args_str = body[len(tokens[0]):].lstrip()
    return cmd, args_str

async def dispatch(ctx) -> CommandResult:
    """
    Dispatch a command to its handler.

    Args:
        ctx: Context object with:
            - anna_user_id: int
            - content: str
            - message: Discord message object
            - role_ids: Optional[list] - Role IDs that trigger the bot

    Returns:
        CommandResult indicating if command was handled and response text
    """
    role_ids = getattr(ctx, 'role_ids', None)
    cmd, args_str = extract_command_from_mention(ctx.content or "", ctx.anna_user_id, role_ids)
    logger.info(f"Dispatching command: {cmd!r} with args: {args_str!r}")

    if not cmd:
        return CommandResult(True, "usage: `@Anna help`")

    from commands import registry
    handler = registry.get(cmd)

    if not handler:
        logger.warning(f"Unknown command: {cmd}")
        return CommandResult(True, f"unknown command `{cmd}` — try `@Anna help`")

    try:
        logger.debug(f"Executing command handler for: {cmd}")
        out = await handler(ctx, args_str)
        logger.info(f"Command {cmd} executed successfully")
        return CommandResult(True, out)
    except ValueError as e:
        logger.warning(f"Command {cmd} - invalid input: {e}")
        return CommandResult(True, f"invalid input: {e}")
    except Exception as e:
        logger.error(f"Command {cmd} failed: {e}", exc_info=True)
        return CommandResult(True, f"command `{cmd}` encountered an error")
