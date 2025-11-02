import shlex
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class CommandResult:
    handled: bool
    text: Optional[str] = None

def _find_anna_mention_span(content: str, anna_user_id: int) -> Optional[Tuple[int, int]]:
    # Accept <@id> and <@!id>
    needles = (f"<@{anna_user_id}>", f"<@!{anna_user_id}>")
    for n in needles:
        i = content.find(n)
        if i != -1:
            return (i, i + len(n))
    return None

def is_command_after_mention(content: str, anna_user_id: int) -> bool:
    span = _find_anna_mention_span(content, anna_user_id)
    if not span:
        return False
    after = content[span[1]:].lstrip()
    return after.startswith(">")

def extract_command_after_mention(content: str, anna_user_id: int) -> Tuple[str, str]:
    span = _find_anna_mention_span(content, anna_user_id)
    if not span:
        return "", ""
    after = content[span[1]:].lstrip()
    if not after.startswith(">"):
        return "", ""
    body = after[1:].lstrip()
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
    ctx:
      - anna_user_id: int
      - content: str
    """
    if not is_command_after_mention(ctx.content or "", ctx.anna_user_id):
        return CommandResult(False)

    cmd, args_str = extract_command_after_mention(ctx.content or "", ctx.anna_user_id)
    if not cmd:
        return CommandResult(True, "usage: `@Anna >help`")

    from anna.vps.commands import registry
    handler = registry.get(cmd)
    if not handler:
        return CommandResult(True, f"unknown command `{cmd}` — try `@Anna >help`")
    try:
        out = await handler(ctx, args_str)
        return CommandResult(True, out)
    except Exception as e:
        return CommandResult(True, f"command `{cmd}` failed: {e}")
