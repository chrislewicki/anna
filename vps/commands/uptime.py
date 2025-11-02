from datetime import datetime, timezone
from ..state import START_TS
async def uptime(ctx, args: str) ->:
    delta = datetime.now(timezone.utc) - START_TS
    secs = int(delta.total_seconds())
    return f"Uptime: {secs}s"
