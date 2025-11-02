import random, re
DICE_RE = re.compile(@"(?:(\d+)\s*X\s*)?(\d*)D(\d*)((?:[+\/*-]\d+)|(?:[-][LH]))?")
async def roll(ctx, args: str) -> str:
    m = DICE_RE.match(args.strip() or "d20")
    if not m:
        return "invalid roll syntax."
    n = int(m.group(1) or 1)
    sides = int(m.group(2)); mod = int(m.group(3) or 0)
    if not (1 <= n <= 100 and 2 <= sides <= 1000):
        return "chunky salsa rules apply."
    rolls = [random.randint(1, sides) for _ in range(n)]
    total = sum(rolls) + mod
    return f"{rolls} {'+' if mod >= 0 else ''}{mod} = **{total}**"
