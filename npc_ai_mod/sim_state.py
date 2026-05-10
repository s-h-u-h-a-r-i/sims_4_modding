"""
sim_state.py — read and serialize NPC Sim data.

Responsible for collecting the current state of NPC Sims and returning it
as plain dicts suitable for JSON serialisation and sending to the AI service.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import services
from clock import ClockSpeedMode

if TYPE_CHECKING:
    from sims.sim_info import SimInfo


def _serialize_super_interaction(si: Any) -> "Dict[str, Any]":
    """Minimal snapshot for the viewer (and future cancel by id)."""
    return {
        "interaction_id": int(si.id),
        "interaction_id_str": str(si.id),
        "class_name": si.__class__.__name__,
    }


def _interactions_for_sim(sim: Any) -> "Dict[str, Any]":
    """What the sim is running now vs what is queued (per EA interaction_commands patterns)."""
    running: List[Dict[str, Any]] = []
    queued: List[Dict[str, Any]] = []

    try:
        for si in sim.si_state.sis_actor_gen():
            running.append(_serialize_super_interaction(si))
    except Exception:
        pass

    try:
        queue = sim.queue
        if queue is not None:
            head = getattr(queue, "running", None)
            for si in queue:
                row = _serialize_super_interaction(si)
                row["is_queue_head"] = bool(head is not None and si is head)
                queued.append(row)
    except Exception:
        pass

    return {
        "interactions_running": running,
        "interactions_queue": queued,
    }


def is_game_paused() -> bool:
    try:
        return services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
    except Exception:
        return False


def get_instanced_sim_infos() -> "List[SimInfo]":
    """Return SimInfo objects for all Sims currently instantiated in the zone."""
    manager = services.sim_info_manager()
    if manager is None:
        return []
    result = []
    for sim_info in manager.values():
        try:
            if sim_info.get_sim_instance() is not None:
                result.append(sim_info)
        except Exception:
            pass
    return result


def serialize_sim(sim_info: "SimInfo") -> "Dict[str, Any]":
    """Convert a SimInfo into a JSON-serialisable dict."""
    out: Dict[str, Any] = {
        "sim_id": int(sim_info.id),
        "sim_id_str": str(sim_info.id),
        "first_name": str(sim_info.first_name),
        "last_name": str(sim_info.last_name),
        "age": sim_info.age.name if sim_info.age is not None else None,
        "gender": sim_info.gender.name if sim_info.gender is not None else None,
        "is_npc": bool(sim_info.is_npc),
        "household_id": (
            int(sim_info.household_id) if sim_info.household_id is not None else None
        ),
        "zone_id": int(sim_info.zone_id) if sim_info.zone_id is not None else None,
    }
    try:
        sim = sim_info.get_sim_instance()
        if sim is not None:
            out.update(_interactions_for_sim(sim))
        else:
            out["interactions_running"] = []
            out["interactions_queue"] = []
    except Exception:
        out["interactions_running"] = []
        out["interactions_queue"] = []
    return out


def get_world_state() -> "Dict[str, Any]":
    """Collect full world snapshot: all instanced Sims + zone/lot context."""
    zone_id: Optional[int] = None
    lot_id: Optional[int] = None

    try:
        raw = services.current_zone_id()
        if raw is not None:
            zone_id = int(raw)
    except Exception:
        pass

    try:
        raw = services.active_lot_id()
        if raw is not None:
            lot_id = int(raw)
    except Exception:
        pass

    sims: List[Dict[str, Any]] = []
    for sim_info in get_instanced_sim_infos():
        try:
            sims.append(serialize_sim(sim_info))
        except Exception:
            pass

    return {"lot_id": lot_id, "zone_id": zone_id, "sims": sims}
