"""
Typed wire / domain shapes for the NPC AI mod (JSON-serialisable via helpers).
"""

from .models import (
    DecisionOutcome,
    LogEntry,
    QueuedInteraction,
    RunningInteraction,
    SerializedSim,
    ServerDecision,
    TickInfo,
    TickPayload,
    TickResponse,
    WorldState,
)
from .wire import (
    log_entry_to_wire,
    parse_tick_response,
    tick_payload_to_wire,
)

__all__ = (
    "RunningInteraction",
    "QueuedInteraction",
    "SerializedSim",
    "WorldState",
    "TickInfo",
    "DecisionOutcome",
    "ServerDecision",
    "TickResponse",
    "LogEntry",
    "TickPayload",
    "log_entry_to_wire",
    "tick_payload_to_wire",
    "parse_tick_response",
)
