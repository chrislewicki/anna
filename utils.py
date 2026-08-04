"""Utility functions for Anna bot."""

import tempfile
import shutil
import json
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_duration_long(seconds: int) -> str:
    """
    Format seconds as a compact multi-unit duration.

    Examples:
        93784 -> "1d 2h 3m 4s"
        3600  -> "1h"
        59    -> "59s"
    """
    seconds = max(0, int(seconds))
    parts = []
    for unit_seconds, label in ((86400, 'd'), (3600, 'h'), (60, 'm')):
        if seconds >= unit_seconds:
            parts.append(f"{seconds // unit_seconds}{label}")
            seconds %= unit_seconds
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def format_track_time(seconds: int) -> str:
    """
    Format seconds as a track timestamp.

    Examples:
        151  -> "2:31"
        3723 -> "1:02:03"
    """
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def atomic_json_save(data: Any, file_path: str) -> None:
    """
    Save JSON data atomically to prevent corruption.

    This function writes to a temporary file first, then atomically moves it
    to the target location. This ensures the file is never partially written,
    preventing corruption if the process crashes during save.

    Args:
        data: Data to serialize to JSON (dict, list, etc.)
        file_path: Target file path

    Raises:
        Exception: If save fails (logged but not raised)
    """
    try:
        dir_path = os.path.dirname(file_path) or '.'

        # Write to temp file in same directory
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=dir_path,
            delete=False,
            suffix='.tmp',
            prefix='.tmp_'
        ) as tmp:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())  # Ensure written to disk
            tmp_name = tmp.name

        # Atomic move (replaces target file)
        shutil.move(tmp_name, file_path)
        logger.debug(f"Atomically saved {file_path}")

    except Exception as e:
        logger.error(f"Failed to save {file_path}: {e}", exc_info=True)
        # Clean up temp file if it exists
        try:
            if 'tmp_name' in locals() and os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass  # Best effort cleanup
