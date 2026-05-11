"""Per-tick activity fingerprinting (coalesces bridge traffic)."""

from __future__ import annotations

import typing
from collections import Counter

import services
from sims.sim import Sim

from .filters import si_class_is_background_noise
from .instanced import get_instanced_sim_infos
from .partner_wire import partner_wire_fingerprint
from .types_defs import (
    ClassMultiset,
    PartnerWireFingerprint,
    SimFingerprintRow,
    WorldFingerprint,
)

__all__ = (
    "ClassMultiset",
    "SimFingerprintRow",
    "PartnerWireFingerprint",
    "WorldFingerprint",
    "world_activity_fingerprint",
    "world_activity_fingerprint_if_stable",
)


def world_activity_fingerprint() -> WorldFingerprint:
    """
    Cheap hashable snapshot of "is the world visibly different since last tick".

    Per Sim: instanced id, running/queued **affordance-class multisets** (not SI ids).
    Used to coalesce bridge traffic — SI ids churn between reads even when gameplay is steady.
    """
    zone_id: typing.Optional[int] = None
    lot_id: typing.Optional[int] = None

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

    rows: typing.List[SimFingerprintRow] = []
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
    partners = partner_wire_fingerprint()
    return (zone_id, lot_id, tuple(rows), partners)


def world_activity_fingerprint_if_stable() -> typing.Optional[WorldFingerprint]:
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


def _si_fingerprint_slices(sim: Sim) -> typing.Tuple[ClassMultiset, ClassMultiset]:
    """
    Running vs queued **class multisets** (how many of each non-noise affordance class).

    Noise classes (idle overlays, passive stances, social picker engine loops) are
    excluded so the fingerprint only changes on meaningful gameplay transitions.
    """

    run_c: Counter[str] = Counter()
    try:
        for si in sim.si_state.sis_actor_gen():
            try:
                name = si.__class__.__name__
                if not si_class_is_background_noise(name):
                    run_c[name] += 1
            except Exception:
                pass
    except Exception:
        pass
    run_tup = tuple(sorted(run_c.items()))

    q_c: Counter[str] = Counter()
    try:
        q = sim.queue
        if q is not None:
            for si in q:
                try:
                    name = si.__class__.__name__
                    if not si_class_is_background_noise(name):
                        q_c[name] += 1
                except Exception:
                    pass
    except Exception:
        pass
    q_tup = tuple(sorted(q_c.items()))

    return (run_tup, q_tup)
