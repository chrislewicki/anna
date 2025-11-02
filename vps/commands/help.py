from . import registry
async def help_cmd(ctx, args: str) -> str:
    cmds = ", ".join(sorted(registry.keys()))
    return f"commands: {cmds} - prefix with `>` (e.g., `>ping`)"
