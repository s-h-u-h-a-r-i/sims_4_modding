import traceback
from typing import Any, Dict, List, Optional

from .utils import iso_utc_now

__all__ = (
    "clear_session_log",
    "commit_pending_logs",
    "log_debug",
    "log_error",
    "log_info",
    "peek_pending_logs",
)

_MAX_BUFFER = 500
_LOG_BUFFER: List[Dict[str, Any]] = []


def log_debug(tag: str, detail: str) -> None:
    _enqueue("debug", tag, detail)


def log_info(tag: str, detail: str) -> None:
    _enqueue("info", tag, detail)


def log_error(tag: str, detail: str, exc: Optional[BaseException] = None) -> None:
    tb: Optional[str] = None
    if exc is not None:
        tb = f"{exc!r}\n{traceback.format_exc()}"
    _enqueue("error", tag, detail, tb)


def clear_session_log() -> None:
    """Reset buffered log entries when the script package loads."""
    _LOG_BUFFER.clear()
    _enqueue("info", "logutil", "Session started (game package load)")


def peek_pending_logs(max_entries: int = 200) -> List[Dict[str, Any]]:
    """Copy up to `max_entries` from the buffer without removing them (for a tick POST draft)."""
    n = min(max_entries, len(_LOG_BUFFER))
    return _LOG_BUFFER[:n]


def commit_pending_logs(count: int) -> None:
    """Drop the first `count` buffered entries after their POST succeeded."""
    if count <= 0:
        return
    cut = min(count, len(_LOG_BUFFER))
    del _LOG_BUFFER[:cut]



def _enqueue(
    level: str, tag: str, message: str, traceback_text: Optional[str] = None
) -> None:
    entry: Dict[str, Any] = {
        "timestamp_utc": iso_utc_now(),
        "level": level,
        "tag": tag,
        "message": message,
    }
    if traceback_text:
        entry["traceback"] = traceback_text
    _LOG_BUFFER.append(entry)
    while len(_LOG_BUFFER) > _MAX_BUFFER:
        _LOG_BUFFER.pop(0)




