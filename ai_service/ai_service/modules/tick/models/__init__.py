"""
Tick-specific domain models (internal to the tick pipeline)

Wire formats live in modules.tick.schemas; cross-cutting DTOs live outside this module.
"""

from dataclasses import dataclass
from typing import Any, Dict

__all__ = ("TickSnapshot",)


@dataclass(frozen=True, kw_only=True)
class TickSnapshot:
    seq: int
    ticks_seen: int | None
    received_at_utc_iso: str | None
    tick_request: Dict[str, Any] | None
    tick_response: Dict[str, Any] | None
    ai_enabled: bool = True
