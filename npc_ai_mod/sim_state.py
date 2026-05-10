"""
sim_state.py — read and serialize NPC Sim data.

Responsible for collecting the current state of NPC Sims and returning it
as plain dicts suitable for JSON serialisation and sending to the AI service.
"""

from collections import Counter
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import services
from clock import ClockSpeedMode

if TYPE_CHECKING:
    from sims.sim_info import SimInfo

def is_game_paused() -> bool:
    try:
        return services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
    except Exception:
        return False

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


# Affordance class names/prefixes excluded from the activity fingerprint.
# These are engine-internal cycling interactions that churn every few seconds
# and carry no signal for AI decisions.
_FP_EXCLUDE_EXACT: frozenset = frozenset({
    'Emotion_Idle',
    'stand_Passive',
    'sit_Passive',
    'SocialPickerSI',   # social picker ticks every ~1.5s as engine background loop
})
_FP_EXCLUDE_PREFIXES: tuple = (
    'Idle_',            # idle overlay animations  (Idle_Age_Teen, etc.)
    'idle_',            # lifestyle / mood idles   (idle_Lifestyles_*, etc.)
    'aggregate_',       # background observers     (aggregate_SocialObservation_*, etc.)
    'reactions_',       # reaction overlays cycle on/off while underlying action continues
)


def _fp_class_is_noise(name: str) -> bool:
    return name in _FP_EXCLUDE_EXACT or name.startswith(_FP_EXCLUDE_PREFIXES)


def _si_fingerprint_slices(sim: Any) -> tuple:
    """
    Running vs queued **class multisets** (how many of each non-noise affordance class).

    Noise classes (idle overlays, passive stances, social picker engine loops) are
    excluded so the fingerprint only changes on meaningful gameplay transitions.
    """
    run_c: Counter = Counter()
    try:
        for si in sim.si_state.sis_actor_gen():
            try:
                name = si.__class__.__name__
                if not _fp_class_is_noise(name):
                    run_c[name] += 1
            except Exception:
                pass
    except Exception:
        pass
    run_tup = tuple(sorted(run_c.items()))

    q_c: Counter = Counter()
    try:
        q = sim.queue
        if q is not None:
            for si in q:
                try:
                    name = si.__class__.__name__
                    if not _fp_class_is_noise(name):
                        q_c[name] += 1
                except Exception:
                    pass
    except Exception:
        pass
    q_tup = tuple(sorted(q_c.items()))

    return (run_tup, q_tup)


def world_activity_fingerprint() -> tuple:
    """
    Cheap hashable snapshot of “is the world visibly different since last tick”.

    Per Sim: instanced id, running/queued **affordance-class multisets** (not SI ids).
    Used to coalesce bridge traffic — SI ids churn between reads even when gameplay is steady.
    """
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

    rows: List[tuple] = []
    for sim_info in get_instanced_sim_infos():
        try:
            sid = int(sim_info.id)
            sim = sim_info.get_sim_instance()
            if sim is None:
                rows.append((sid, (), ()))
                continue
            run_tup, q_tup = _si_fingerprint_slices(sim)
            rows.append((sid, run_tup, q_tup))
        except Exception:
            pass

    rows.sort(key=lambda r: r[0])
    return (zone_id, lot_id, tuple(rows))


def fingerprint_diff(old: Optional[tuple], new: Optional[tuple]) -> str:
    """
    Human-readable summary of what changed between two world_activity_fingerprint() tuples.
    Used only for debug logging — not called in the hot path.
    Format: (zone_id, lot_id, ((sim_id, run_tup, q_tup), ...))
    """
    if old is None:
        return "(no previous fingerprint)"
    if new is None:
        return "(new fingerprint is None)"
    old_sims: Dict[int, tuple] = {row[0]: row for row in old[2]}
    new_sims: Dict[int, tuple] = {row[0]: row for row in new[2]}
    parts: List[str] = []
    if old[:2] != new[:2]:
        parts.append(f"zone/lot {old[:2]} → {new[:2]}")
    all_ids = sorted(set(old_sims) | set(new_sims))
    for sid in all_ids:
        o = old_sims.get(sid)
        n = new_sims.get(sid)
        if o is None:
            parts.append(f"sim {sid} appeared")
        elif n is None:
            parts.append(f"sim {sid} left")
        else:
            o_run, o_q = o[1], o[2]
            n_run, n_q = n[1], n[2]
            if o_run != n_run:
                parts.append(f"sim {sid} running {dict(o_run)} → {dict(n_run)}")
            if o_q != n_q:
                parts.append(f"sim {sid} queued {dict(o_q)} → {dict(n_q)}")
    return "; ".join(parts) if parts else "(no visible diff)"


def world_activity_fingerprint_if_stable() -> Optional[tuple]:
    """
    Two back-to-back fingerprints must match, or we return None.

    Extra guard while the sim queue moves between script callbacks; class multisets make
    mismatches rarer than with SI ids.
    """
    a = world_activity_fingerprint()
    b = world_activity_fingerprint()
    if a == b:
        return a
    return None


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
