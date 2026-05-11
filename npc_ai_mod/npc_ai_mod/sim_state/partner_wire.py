"""Shared non-Sim object cohorts merged into ``social_partner_sim_ids`` on the wire."""

from __future__ import annotations

import typing

from interactions.base.super_interaction import SuperInteraction
from sims.sim import Sim

from ..schemas import SerializedSim
from ._filters import si_class_excluded_from_activity_object_merge
from ._iteration import iter_actor_and_queue_super_interactions
from .instanced import get_instanced_sim_infos
from .partners import social_partner_sim_ids, strict_partner_sim_id
from .types_defs import PartnerWireFingerprint


def _activity_object_id_from_si(si: SuperInteraction) -> typing.Optional[int]:
    """
    Object id for **shared prop** activities (arcade, trivia box, group craft, etc.): any
    non-background SI whose ``target`` is not a Sim. No per-game class allowlist.
    """
    try:
        cn = si.__class__.__name__
    except Exception:
        return None
    if si_class_excluded_from_activity_object_merge(cn):
        return None
    t = getattr(si, "target", None)
    if t is None or strict_partner_sim_id(t) is not None:
        return None
    tid = getattr(t, "id", None)
    if tid is None:
        return None
    try:
        return int(tid)
    except Exception:
        return None


def _activity_object_ids_for_sim(sim: Sim) -> typing.Set[int]:
    oids: typing.Set[int] = set()
    for si in iter_actor_and_queue_super_interactions(sim):
        oid = _activity_object_id_from_si(si)
        if oid is not None:
            oids.add(oid)
    return oids


def _partner_graph_instanced_wire() -> typing.Dict[int, typing.Set[int]]:
    """
    Canonical partner sets for serialized/wire Sims: SI-derived social graph
    plus shared non-Sim object cohorts (matches ``social_partner_sim_ids`` on payloads).
    """
    by_sid: typing.Dict[int, typing.Set[int]] = {}
    oid_to_players: typing.Dict[int, typing.Set[int]] = {}
    infos = get_instanced_sim_infos()

    for sim_info in infos:
        try:
            sid = int(sim_info.id)
        except Exception:
            continue
        sim = sim_info.get_sim_instance()
        if sim is None:
            by_sid.setdefault(sid, set())
            continue
        raw = social_partner_sim_ids(sim, sid)
        by_sid[sid] = set(raw)
        for oid in _activity_object_ids_for_sim(sim):
            oid_to_players.setdefault(oid, set()).add(sid)

    for cohort in oid_to_players.values():
        if len(cohort) < 2:
            continue
        for sid in cohort:
            by_sid.setdefault(sid, set()).update(x for x in cohort if x != sid)

    return by_sid


def partner_wire_fingerprint() -> PartnerWireFingerprint:
    """Fourth component of ``WorldFingerprint`` — keeps POSTs flowing when cohorts churn."""
    g = _partner_graph_instanced_wire()
    return tuple((sid, tuple(sorted(mates))) for sid, mates in sorted(g.items()))


def merge_shared_activity_object_partners_into_sims(
    sims: typing.List[SerializedSim],
) -> None:
    merged = _partner_graph_instanced_wire()
    lookup = {int(s.sim_id): s for s in sims}
    for sid, row in lookup.items():
        row.social_partner_sim_ids = sorted(merged.get(sid, set()))
