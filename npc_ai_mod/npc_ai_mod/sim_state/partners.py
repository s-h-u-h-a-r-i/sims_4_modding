"""Derive other Sim ids from running/queued SuperInteraction participant graph."""

from __future__ import annotations

import typing

from interactions.base.super_interaction import SuperInteraction
from sims.sim import Sim
from sims.sim_info import SimInfo

from ._iteration import iter_actor_and_queue_super_interactions

_SOCIAL_GROUP_MEMBER_ATTRS: typing.Tuple[str, ...] = (
    "_sim_infos",
    "sim_infos",
    "participant_sim_infos",
    "_participant_sim_infos",
    "sim_info_gen",
    "_sim_info_gen",
)
_LIABILITY_SIM_ATTRS: typing.Tuple[str, ...] = (
    "target_sim",
    "_target_sim",
    "target_sim_info",
    "_target_sim_info",
    "participant_sim_info",
    "_participant_sim_info",
    "picked_sim_info",
    "_picked_sim_info",
    "sim_info",
    "_sim_info",
    "sim",
    "_sim",
)
_SI_CHILD_BAG_ATTRS: typing.Tuple[str, ...] = (
    "_interactions",
    "interactions",
    "_mixer_interactions",
    "mixer_interactions",
)

_PARTNER_GRAPH_MAX_DEPTH = 5


def strict_partner_sim_id(obj: typing.Any) -> typing.Optional[int]:
    """Only count explicit Sim/SimInfo — avoids GameObject ``id`` mistaken for a Sim id."""
    if obj is None:
        return None
    if isinstance(obj, SimInfo):
        try:
            return int(obj.id)
        except Exception:
            return None
    if isinstance(obj, Sim):
        try:
            return int(obj.id)
        except Exception:
            pass
        try:
            si = getattr(obj, "sim_info", None)
            if isinstance(si, SimInfo):
                return int(si.id)
        except Exception:
            pass
        return None
    return None


def _ids_from_maybe_iterable(coll: typing.Any) -> typing.Iterable[int]:
    if coll is None:
        return ()
    try:
        if callable(coll):
            coll = coll()
    except Exception:
        return ()
    try:
        items = tuple(coll)
    except TypeError:
        return ()
    out: typing.List[int] = []
    for item in items:
        sid = strict_partner_sim_id(item)
        if sid is not None:
            out.append(sid)
            continue
        # Some engines store (enum, SimInfo)-style tuples in group blobs.
        if isinstance(item, (tuple, list)) and len(item) <= 8:
            for slot in item:
                sid_inner = strict_partner_sim_id(slot)
                if sid_inner is not None:
                    out.append(sid_inner)
    return out


def _social_group_member_sim_ids(sg: typing.Any, self_sim_id: int) -> typing.Set[int]:
    out: typing.Set[int] = set()
    if sg is None:
        return out
    for attr in _SOCIAL_GROUP_MEMBER_ATTRS:
        try:
            coll = getattr(sg, attr, None)
        except Exception:
            continue
        for sid in _ids_from_maybe_iterable(coll):
            if sid != self_sim_id:
                out.add(int(sid))
    return out


def _gather_child_super_interactions(
    si: SuperInteraction,
) -> typing.List[SuperInteraction]:
    out: typing.List[SuperInteraction] = []
    seen: typing.Set[int] = set()
    for attr in _SI_CHILD_BAG_ATTRS:
        try:
            bag = getattr(si, attr, None)
        except Exception:
            continue
        if bag is None:
            continue
        try:
            items = tuple(bag)
        except Exception:
            continue
        for x in items:
            if isinstance(x, SuperInteraction):
                i = id(x)
                if i not in seen:
                    seen.add(i)
                    out.append(x)
    return out


def _partner_ids_from_liabilities(
    si: SuperInteraction, self_sim_id: int
) -> typing.Set[int]:
    found: typing.Set[int] = set()
    bag = getattr(si, "_liabilities", None)
    if bag is None:
        return found
    try:
        items = tuple(bag)
    except Exception:
        return found
    for li in items:
        for attr in _LIABILITY_SIM_ATTRS:
            try:
                o = getattr(li, attr, None)
            except Exception:
                continue
            sid = strict_partner_sim_id(o)
            if sid is not None and sid != self_sim_id:
                found.add(sid)
        for aid in (
            "target_sim_id",
            "_target_sim_id",
            "picked_sim_id",
            "_picked_sim_id",
            "sim_id",
            "_sim_id",
        ):
            try:
                raw = getattr(li, aid, None)
            except Exception:
                continue
            if raw is None:
                continue
            try:
                n = int(raw)
            except Exception:
                continue
            if n != self_sim_id:
                found.add(n)
    return found


def _partner_ids_from_kwargs(si: SuperInteraction, self_sim_id: int) -> typing.Set[int]:
    found: typing.Set[int] = set()
    kw = getattr(si, "_kwargs", None)
    if not isinstance(kw, dict):
        return found

    def _eat(obj: typing.Any, nest: int) -> None:
        if nest > 6:
            return
        sid = strict_partner_sim_id(obj)
        if sid is not None and sid != self_sim_id:
            found.add(sid)
            return
        if isinstance(obj, (tuple, list, set)):
            for x in tuple(obj)[:24]:
                _eat(x, nest + 1)
        elif isinstance(obj, dict):
            for v in list(obj.values())[:24]:
                _eat(v, nest + 1)

    for key in kw:
        try:
            _eat(kw.get(key), 0)
        except Exception:
            pass
    return found


def _partner_ids_from_super_interaction(
    si: SuperInteraction, self_sim_id: int, depth: int = 0
) -> typing.Set[int]:
    found: typing.Set[int] = set()
    if si is None or depth > _PARTNER_GRAPH_MAX_DEPTH:
        return found
    for attr in ("target", "interaction_target"):
        try:
            t = getattr(si, attr, None)
        except Exception:
            continue
        sid = strict_partner_sim_id(t)
        if sid is not None and sid != self_sim_id:
            found.add(sid)

    sg = getattr(si, "_social_group", None)
    found |= _social_group_member_sim_ids(sg, self_sim_id)
    found |= _partner_ids_from_liabilities(si, self_sim_id)
    found |= _partner_ids_from_kwargs(si, self_sim_id)

    for child in _gather_child_super_interactions(si):
        if child is si:
            continue
        found |= _partner_ids_from_super_interaction(child, self_sim_id, depth + 1)
    return found


def _all_super_interactions_on_sim(sim: Sim) -> typing.List[SuperInteraction]:
    return list(iter_actor_and_queue_super_interactions(sim))


def social_partner_sim_ids(sim: Sim, self_sim_id: int) -> typing.List[int]:
    """Other Sims reachable from explicit social-ish SI participant state."""
    uniq: typing.Set[int] = set()
    try:
        for si in _all_super_interactions_on_sim(sim):
            uniq |= _partner_ids_from_super_interaction(si, self_sim_id)
    except Exception:
        pass
    return sorted(uniq)
