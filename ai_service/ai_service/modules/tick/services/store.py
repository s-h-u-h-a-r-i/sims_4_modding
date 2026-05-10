import threading
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Self

from ai_service.modules.tick.models import TickSnapshot

__all__ = ("TickStore",)


class TickStore:
    _instance: ClassVar[Self | None] = None
    _lock = threading.Lock()
    _tick_count = 0
    _last: TickSnapshot | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            setattr(self, "_initialized", True)

    def record_tick(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        with self._lock:
            self._tick_count += 1
            self._last = TickSnapshot(
                seq=self._tick_count,
                ticks_seen=None,
                received_at_utc_iso=datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                tick_request=request,
                tick_response=response,
            )

    def get_snapshot(self) -> TickSnapshot:
        with self._lock:
            if self._last is None:
                return TickSnapshot(
                    seq=0,
                    ticks_seen=self._tick_count,
                    received_at_utc_iso=None,
                    tick_request=None,
                    tick_response=None,
                )
            return self._last
