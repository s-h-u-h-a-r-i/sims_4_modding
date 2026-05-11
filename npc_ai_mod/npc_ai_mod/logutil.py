import traceback
import typing

from .schemas import LogEntry
from .utils import iso_utc_now

_MAX_BUFFER = 500
_LOG_BUFFER: typing.List[LogEntry] = []


def log_debug(tag: str, detail: str) -> None:
    _enqueue("debug", tag, detail)


def log_info(tag: str, detail: str) -> None:
    _enqueue("info", tag, detail)


def log_error(
    tag: str, detail: str, exc: typing.Optional[BaseException] = None
) -> None:
    tb: typing.Optional[str] = None
    if exc is not None:
        tb = f"{exc!r}\n{traceback.format_exc()}"
    _enqueue("error", tag, detail, tb)


def clear_session_log() -> None:
    """Called on script reload; wipes any lines not yet drained for a POST."""
    _LOG_BUFFER.clear()
    _enqueue("info", "logutil", "Session started (game package load)")


def drain_logs_for_tick(
    max_entries: int = 250,
) -> typing.List[LogEntry]:
    """Take up to `max_entries` from the head of the pending list and remove them.

    Entries are bundled on the outgoing tick body; persistence is viewer-only.
    If the POST fails, these lines are not re-sent from the mod.
    """
    n = min(max_entries, len(_LOG_BUFFER))
    if n <= 0:
        return []
    batch = list(_LOG_BUFFER[:n])
    del _LOG_BUFFER[:n]
    return batch


def _enqueue(
    level: str, tag: str, message: str, traceback_text: typing.Optional[str] = None
) -> None:
    entry = LogEntry(
        timestamp_utc=iso_utc_now(),
        level=level,
        tag=tag,
        message=message,
        traceback=traceback_text,
    )
    _LOG_BUFFER.append(entry)
    while len(_LOG_BUFFER) > _MAX_BUFFER:
        _LOG_BUFFER.pop(0)
