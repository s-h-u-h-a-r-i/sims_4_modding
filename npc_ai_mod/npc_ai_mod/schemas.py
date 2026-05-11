"""
Typed wire / domain shapes for the NPC AI mod (JSON-serialisable via helpers).
"""

from __future__ import annotations

import typing as t
from dataclasses import asdict, dataclass, field


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


def log_entry_to_wire(le: LogEntry) -> t.Dict[str, t.Any]:
    d: t.Dict[str, t.Any] = {
        "timestamp_utc": le.timestamp_utc,
        "level": le.level,
        "tag": le.tag,
        "message": le.message,
    }
    if le.traceback is not None:
        d["traceback"] = le.traceback
    return d


def tick_payload_to_wire(p: TickPayload) -> t.Dict[str, t.Any]:
    def _serialized_sim_to_wire(sim: SerializedSim) -> t.Dict[str, t.Any]:
        d = asdict(sim)
        # JavaScript loses integer precision beyond 2^53-1 — keep bigint-like fields as decimals.
        d["sim_id"] = str(sim.sim_id)
        d["social_partner_sim_ids"] = [str(pid) for pid in sim.social_partner_sim_ids]
        return d

    world = asdict(p.world)
    world["sims"] = [_serialized_sim_to_wire(s) for s in p.world.sims]
    body: t.Dict[str, t.Any] = {
        "tick": asdict(p.tick),
        "world": world,
    }
    if p.outcomes:
        body["outcomes"] = [asdict(o) for o in p.outcomes]
    if p.logs:
        body["logs"] = [log_entry_to_wire(l) for l in p.logs]
    return body


def parse_tick_response(raw: t.Dict[str, t.Any]) -> TickResponse:
    raw_decisions = raw.get("decisions") or []
    decisions: t.List[ServerDecision] = []
    if isinstance(raw_decisions, list):
        for item in raw_decisions:
            if isinstance(item, dict):
                decisions.append(_server_decision_from_wire(item))
    return TickResponse(
        protocol_version=raw.get("protocol_version"),
        decisions=decisions,
    )


def _server_decision_from_wire(row: t.Dict[str, t.Any]) -> ServerDecision:
    return ServerDecision(
        decision_id=row.get("id"),
        action=row.get("action"),
        sim_id=row.get("sim_id"),
    )
