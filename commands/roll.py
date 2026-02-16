"""Dice rolling command implementation."""

import random
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext

DICE_RE = re.compile(r"(?:(\d+)\s*X\s*)?(\d*)D(\d*)((?:[+\/*-]\d+)|(?:[-][LH]))?", re.I)


async def roll(ctx: 'CommandContext', args: str) -> str:
    """
    Roll dice using standard RPG notation.

    Supports formats like:
    - d20 (default: 1d20)
    - 2d6 (2 six-sided dice)
    - 3d8+5 (3 eight-sided dice plus 5)
    - 5x d20 (repeat roll 5 times)

    Args:
        ctx: Command context
        args: Dice notation string

    Returns:
        Dice roll results and total
    """
    m = DICE_RE.match(args.strip() or "d20")
    if not m:
        return "invalid roll syntax."

    repeat = int(m.group(1) or 1)
    num_dice = int(m.group(2) or 1)
    sides = int(m.group(3) or 20)
    mod_str = m.group(4) or ""

    # Parse modifier
    mod = 0
    if mod_str and mod_str not in ["-L", "-H"]:
        mod = int(mod_str)

    if not (1 <= num_dice <= 100 and 2 <= sides <= 1000):
        return "chunky salsa rules apply."

    if repeat > 1:
        # Multiple rolls
        results = []
        for _ in range(repeat):
            rolls = [random.randint(1, sides) for _ in range(num_dice)]
            total = sum(rolls) + mod
            results.append(total)
        return f"{results} = **{sum(results)}**"
    else:
        # Single roll
        rolls = [random.randint(1, sides) for _ in range(num_dice)]
        total = sum(rolls) + mod
        mod_display = f" {'+' if mod >= 0 else ''}{mod}" if mod != 0 else ""
        return f"{rolls}{mod_display} = **{total}**"
