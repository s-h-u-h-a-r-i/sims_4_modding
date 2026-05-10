import threading
from collections import deque
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, List

from ai_service.modules.tick.models import TickSnapshot

__all__ = ("TickStore",)


class TickStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tick_count = 0
        self._last: TickSnapshot | None = None
        self._ai_enabled: bool = True
        self._command_queue: deque[Dict[str, Any]] = deque(maxlen=50)

    def set_ai_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._ai_enabled = enabled

    def is_ai_enabled(self) -> bool:
        with self._lock:
            return self._ai_enabled

    def push_command(self, command: Dict[str, Any]) -> None:
        with self._lock:
            self._command_queue.append(command)

    def pop_commands(self) -> List[Dict[str, Any]]:
        with self._lock:
            commands = list(self._command_queue)
            self._command_queue.clear()
            return commands

    def record_tick(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        with self._lock:
            self._tick_count += 1
            self._last = TickSnapshot(
                seq=self._tick_count,
                ticks_seen=None,
                received_at_utc_iso=datetime.now(timezone.utc).isoformat(),
                tick_request=request,
                tick_response=response,
                ai_enabled=self._ai_enabled,
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
                    ai_enabled=self._ai_enabled,
                )
            # Always reflect current ai_enabled, not what it was at last tick
            return replace(self._last, ai_enabled=self._ai_enabled)
