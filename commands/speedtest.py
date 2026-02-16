"""Network speed test command implementation."""

import logging
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from message_handler import CommandContext

logger = logging.getLogger(__name__)


async def speedtest(ctx: 'CommandContext', args: str) -> str:
    """
    Run a network speed test.

    Measures download speed, upload speed, and ping using Speedtest.net.
    Note: This can take 15-30 seconds to complete.

    Usage: @Anna >speedtest

    Args:
        ctx: Command context
        args: Command arguments (unused)

    Returns:
        Formatted speed test results
    """
    try:
        # Import here to avoid issues if library not installed
        import speedtest as st
    except ImportError:
        logger.error("speedtest-cli library not installed")
        return "speed test unavailable (library not installed)"

    try:
        logger.info("Starting speed test...")

        # Run speedtest in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_speedtest)

        logger.info(f"Speed test completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Speed test failed: {e}", exc_info=True)
        return f"speed test failed: {type(e).__name__}"


def _run_speedtest() -> str:
    """
    Synchronous speed test runner (executed in thread pool).

    Returns:
        Formatted speed test results string
    """
    import speedtest as st

    # Create speedtest instance
    speed = st.Speedtest()

    # Get best server based on ping
    speed.get_best_server()

    # Run download test
    download_bps = speed.download()
    download_mbps = download_bps / 1_000_000  # Convert to Mbps

    # Run upload test
    upload_bps = speed.upload()
    upload_mbps = upload_bps / 1_000_000  # Convert to Mbps

    # Get ping
    ping_ms = speed.results.ping

    # Get server info
    server = speed.results.server
    server_name = server.get('sponsor', 'Unknown')
    server_location = f"{server.get('name', '')}, {server.get('country', '')}"

    # Format results
    return (
        f"**Speed Test Results**\n"
        f"Download: **{download_mbps:.1f} Mbps**\n"
        f"Upload: **{upload_mbps:.1f} Mbps**\n"
        f"Ping: **{ping_ms:.1f} ms**\n"
        f"Server: {server_name} ({server_location})"
    )
