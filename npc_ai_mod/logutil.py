import os
import traceback
from typing import Optional

__all__ = ("clear_session_log", "log_error")

FILE_LOG_NAME = "npc_ai_mod.log"


def _file_log_path() -> str:

    norm = os.path.normpath(os.path.abspath(__file__))
    parts = norm.split(os.sep)
    for i, segment in enumerate(parts):
        if segment.lower().endswith(".ts4script"):
            archive_path = os.sep.join(parts[: i + 1])
            parent = os.path.dirname(archive_path)
            return os.path.join(parent, FILE_LOG_NAME)
    # Loose scripts (no ts4script in path): log next to this package.
    return os.path.join(os.path.dirname(norm), FILE_LOG_NAME)


def clear_session_log() -> None:
    """Truncate companion log beside the ``.ts4script`` (each package load)."""
    path = _file_log_path()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("Session log started (package load)\n")
    except OSError:
        pass


def log_error(tag: str, detail: str, exc: Optional[BaseException] = None) -> None:
    """Append a bridge/runtime error to the companion log file."""
    body = f"[{tag}] {detail}"
    if exc is not None:
        body = f"{body}\n{exc!r}\n{traceback.format_exc()}"
    path = _file_log_path()
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(body)
            if not body.endswith("\n"):
                fh.write("\n")
    except OSError:
        pass
