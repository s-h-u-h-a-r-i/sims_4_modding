"""
Tick-specific domain models (internal to the tick pipeline)

Wire formats live in modules.tick.schemas; cross-cutting DTOs live outside this module.
"""

from dataclasses import dataclass, field
from typing import Literal, TypedDict

__all__ = (
    "DecisionHistoryWire",
    "DecisionRecord",
    "DecisionRecordStatus",
    "DecisionRecordWire",
    "TickSnapshot",
)

DecisionRecordStatus = Literal["pending", "dispatched", "success", "failure"]


class DecisionRecordWire(TypedDict):
    """JSON-serialisable row for viewer snapshot ``decision_history``."""

    id: str
    sim_id: str
    action: str
    queued_at_utc_iso: str
    dispatched_at_utc_iso: str | None
    status: DecisionRecordStatus
    reason: str | None


DecisionHistoryWire = dict[str, list[DecisionRecordWire]]


def decision_record_to_wire(record: "DecisionRecord") -> DecisionRecordWire:
    """Narrow projection for websocket / ``state.json`` history."""
    return {
        "id": record.id,
        "sim_id": record.sim_id,
        "action": record.action,
        "queued_at_utc_iso": record.queued_at_utc_iso,
        "dispatched_at_utc_iso": record.dispatched_at_utc_iso,
        "status": record.status,
        "reason": record.reason,
    }


@dataclass(kw_only=True)
class DecisionRecord:
    id: str
    sim_id: str
    action: str
    queued_at_utc_iso: str
    dispatched_at_utc_iso: str | None = None
    status: DecisionRecordStatus = "pending"
    reason: str | None = None


@dataclass(frozen=True, kw_only=True)
class TickSnapshot:
    seq: int
    received_at_utc_iso: str | None
    ai_enabled: bool = True
    decision_history: DecisionHistoryWire = field(default_factory=dict)
    bridge_session_id: str | None = None
