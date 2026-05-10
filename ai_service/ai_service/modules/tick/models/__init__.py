"""
Tick-specific domain models (internal to the tick pipeline)

Wire formats live in modules.tick.schemas; cross-cutting DTOs live outside this module.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

__all__ = ("DecisionRecord", "TickSnapshot")


@dataclass(kw_only=True)
class DecisionRecord:
    id: str
    sim_id: str
    action: str
    queued_at_utc_iso: str
    dispatched_at_utc_iso: str | None = None
    status: str = "pending"  # "pending" | "dispatched" | "success" | "failure"
    reason: str | None = None


@dataclass(frozen=True, kw_only=True)
class TickSnapshot:
    seq: int
    ticks_seen: int | None
    received_at_utc_iso: str | None
    tick_request: Dict[str, Any] | None
    tick_response: Dict[str, Any] | None
    ai_enabled: bool = True
    decision_history: Dict[str, Any] = field(default_factory=dict)
