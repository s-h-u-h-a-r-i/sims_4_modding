"""
sim_state.py — read and serialize NPC Sim data.

Responsible for collecting the current state of NPC Sims and returning it
as plain dicts suitable for JSON serialisation and sending to the AI service.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import services

if TYPE_CHECKING:
    from sims.sim_info import SimInfo


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
    return {
        "sim_id": int(getattr(sim_info, "id", 0)),
        "first_name": str(getattr(sim_info, "first_name", "")),
        "last_name": str(getattr(sim_info, "last_name", "")),
        "age": getattr(getattr(sim_info, "age", None), "name", None),
        "gender": getattr(getattr(sim_info, "gender", None), "name", None),
        "is_npc": bool(getattr(sim_info, "is_npc", False)),
        "household_id": (
            int(getattr(sim_info, "household_id", 0))
            if getattr(sim_info, "household_id", None) is not None
            else None
        ),
    }


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
