"""In-memory copy of the most recent tick for local debugging / HTML viewer."""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_tick_count = 0
_last: dict[str, Any] | None = None


def get_snapshot() -> dict[str, Any]:
    """Return JSON-serializable dict; omit tick payload until the first POST."""

    with _lock:
        if _last is None:
            return {
                "seq": 0,
                "ticks_seen": _tick_count,
                "received_at_utc_iso": None,
                "tick_request": None,
                "tick_response": None,
            }
        return dict(_last)
