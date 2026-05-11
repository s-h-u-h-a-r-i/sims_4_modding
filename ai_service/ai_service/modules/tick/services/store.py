import threading
from collections import deque
from datetime import datetime, timezone
from typing import Iterable, List
from uuid import uuid4

from ai_service.modules.tick.models import (
    DecisionHistoryWire,
    DecisionRecord,
    TickSnapshot,
    decision_record_to_wire,
)
from ai_service.modules.tick.schemas import DecisionItemSchema, OutcomeSchema, ViewerCommandWsSchema

__all__ = ("TickStore",)

_HISTORY_PER_SIM = 50
_ID_INDEX_MAX = 500


class TickStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tick_count = 0
        self._bridge_session_id: str | None = None
        self._last_received_at_utc_iso: str | None = None
        self._ai_enabled: bool = True
        self._command_queue: deque[DecisionItemSchema] = deque(maxlen=50)
        self._decision_history: dict[str, deque[DecisionRecord]] = {}
        # best-effort: entries may be evicted from the deque before an outcome arrives
        self._record_by_id: dict[str, DecisionRecord] = {}

    def set_ai_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._ai_enabled = enabled

    def is_ai_enabled(self) -> bool:
        with self._lock:
            return self._ai_enabled

    def push_command(self, command: ViewerCommandWsSchema) -> None:
        sim_id_norm = str(command.sim_id)
        record = DecisionRecord(
            id=str(uuid4()),
            sim_id=sim_id_norm,
            action=command.action,
            queued_at_utc_iso=datetime.now(timezone.utc).isoformat(),
        )
        item = command.to_decision_item(record.id)
        with self._lock:
            self._command_queue.append(item)
            if sim_id_norm not in self._decision_history:
                self._decision_history[sim_id_norm] = deque(maxlen=_HISTORY_PER_SIM)
            self._decision_history[sim_id_norm].append(record)
            if len(self._record_by_id) >= _ID_INDEX_MAX:
                try:
                    oldest_key = next(iter(self._record_by_id))
                    del self._record_by_id[oldest_key]
                except StopIteration:
                    pass
            self._record_by_id[record.id] = record

    def ensure_bridge_session(self, session_id: str | None) -> None:
        """Drop cross-session queues/history when the game mod reloads (new bridge session id)."""
        if not session_id:
            return
        with self._lock:
            if session_id == self._bridge_session_id:
                return
            self._bridge_session_id = session_id
            self._tick_count = 0
            self._last_received_at_utc_iso = None
            self._command_queue.clear()
            self._decision_history.clear()
            self._record_by_id.clear()

    def pop_commands(self) -> List[DecisionItemSchema]:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            commands = list(self._command_queue)
            self._command_queue.clear()
            for cmd in commands:
                rec = self._record_by_id.get(cmd.id)
                if rec is not None:
                    rec.status = "dispatched"
                    rec.dispatched_at_utc_iso = now_iso
            return commands

    def record_outcomes(self, outcomes: Iterable[OutcomeSchema]) -> None:
        with self._lock:
            for outcome in outcomes:
                rec = self._record_by_id.get(outcome.decision_id)
                if rec is None:
                    continue
                rec.status = outcome.status
                rec.reason = outcome.reason

    def note_tick_received(self) -> None:
        with self._lock:
            self._tick_count += 1
            self._last_received_at_utc_iso = datetime.now(timezone.utc).isoformat()

    def get_snapshot(self) -> TickSnapshot:
            history = self._serialise_history()
            return TickSnapshot(
                seq=self._tick_count,
                received_at_utc_iso=self._last_received_at_utc_iso,
                ai_enabled=self._ai_enabled,
                decision_history=history,
                bridge_session_id=self._bridge_session_id,
            )

    def _serialise_history(self) -> DecisionHistoryWire:
        """Must be called under self._lock."""
        return {
            sim_id: [decision_record_to_wire(r) for r in records]
            for sim_id, records in self._decision_history.items()
        }
