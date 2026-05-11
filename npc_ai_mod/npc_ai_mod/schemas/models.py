"""
Typed wire / domain shapes for the NPC AI mod (JSON-serialisable via helpers).
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass, field


@dataclass
class RunningInteraction:
    interaction_id: int
    interaction_id_str: str
    class_name: str


@dataclass
class QueuedInteraction:
    interaction_id: int
    interaction_id_str: str
    class_name: str
    is_queue_head: bool


@dataclass
class SerializedSim:
    """Per-Sim snapshot. ``social_partner_sim_ids``: other Sims in running/queued SI

    participant state (targets + optional ``_social_group`` member lists).

    Sorted unique ints excluding ``sim_id``.
    """

    sim_id: int
    sim_id_str: str
    first_name: str
    last_name: str
    age: t.Optional[str]
    gender: t.Optional[str]
    is_npc: bool
    household_id: t.Optional[int]
    zone_id: t.Optional[int]
    interactions_running: t.List[RunningInteraction]
    interactions_queue: t.List[QueuedInteraction]
    social_partner_sim_ids: t.List[int] = field(default_factory=list)


@dataclass
class WorldState:
    lot_id: t.Optional[int]
    zone_id: t.Optional[int]
    sims: t.List[SerializedSim]


@dataclass
class TickInfo:
    id: int
    timestamp_utc: str
    bridge_session_id: str


@dataclass
class DecisionOutcome:
    decision_id: t.Any
    status: str
    reason: t.Optional[str] = None


@dataclass
class ServerDecision:
    """One decision object from ``POST /v1/tick`` JSON (``id``/``action``/``sim_id``)."""

    decision_id: t.Any
    action: t.Optional[str] = None
    sim_id: t.Any = None


@dataclass
class TickResponse:
    protocol_version: t.Optional[str] = None
    decisions: t.List[ServerDecision] = field(default_factory=list)


@dataclass
class LogEntry:
    timestamp_utc: str
    level: str
    tag: str
    message: str
    traceback: t.Optional[str] = None


@dataclass
class TickPayload:
    tick: TickInfo
    world: WorldState
    outcomes: t.List[DecisionOutcome] = field(default_factory=list)
    logs: t.List[LogEntry] = field(default_factory=list)
