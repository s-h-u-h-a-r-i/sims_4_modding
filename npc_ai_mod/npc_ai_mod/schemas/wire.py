"""JSON wire conversion for tick payloads and responses."""

from __future__ import annotations

import typing as t
from dataclasses import asdict

from .models import LogEntry, SerializedSim, ServerDecision, TickPayload, TickResponse

__all__ = (
    "log_entry_to_wire",
    "tick_payload_to_wire",
    "parse_tick_response",
)


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
