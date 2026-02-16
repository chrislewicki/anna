"""Utility functions for Anna bot."""

import tempfile
import shutil
import json
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


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
