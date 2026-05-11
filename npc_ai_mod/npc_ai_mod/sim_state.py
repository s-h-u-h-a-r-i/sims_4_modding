"""
sim_state.py — read and serialize NPC Sim data.

Responsible for collecting the current state of NPC Sims and returning
serialisable snapshots (see ``schemas``) for the AI bridge.
"""

from __future__ import annotations

import typing
from collections import Counter

import services
from interactions.base.super_interaction import SuperInteraction
from sims.sim import Sim
from sims.sim_info import SimInfo

from .config import LOG_STAGING_MAX, VERBOSE_SIM_INTERACTION_DUMP
from .logutil import log_debug, set_max_log_buffer
from .schemas import QueuedInteraction, RunningInteraction, SerializedSim, WorldState

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

# Same sets used for activity fingerprints and shared-object cohort detection.
_FP_EXCLUDE_EXACT: frozenset = frozenset(
    {
        "Emotion_Idle",
        "stand_Passive",
        "sit_Passive",
        "SocialPickerSI",  # social picker ticks ~1.5s as engine loop
    }
)
_FP_EXCLUDE_PREFIXES: typing.Tuple[str, ...] = (
    "Idle_",
    "idle_",
    "aggregate_",
    "reactions_",
)


def _si_class_is_background_noise(class_name: str) -> bool:
    return class_name in _FP_EXCLUDE_EXACT or class_name.startswith(
        _FP_EXCLUDE_PREFIXES
    )


def _si_class_excluded_from_activity_object_merge(class_name: str) -> bool:
    """Filter out locomotion/noise shells that often target non-Sim objects spuriously."""
    if _si_class_is_background_noise(class_name):
        return True
    nl = class_name.lower()
    compact = nl.replace("-", "").replace("_", "")
    if "gohome" in compact:
        return True
    if nl.startswith("go_here") or nl.startswith("gohere"):
        return True
    if nl.startswith("routing"):
        return True
    if nl == "sim-stand":
        return True
    if (
        "leave_lot" in compact
        or "leavelot" in compact
        or compact.startswith("npc_leave")
    ):
        return True
    return False


def _strict_partner_sim_id(obj: typing.Any) -> typing.Optional[int]:
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
        sid = _strict_partner_sim_id(item)
        if sid is not None:
            out.append(sid)
            continue
        # Some engines store (enum, SimInfo)-style tuples in group blobs.
        if isinstance(item, (tuple, list)) and len(item) <= 8:
            for slot in item:
                sid_inner = _strict_partner_sim_id(slot)
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
            sid = _strict_partner_sim_id(o)
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
        sid = _strict_partner_sim_id(obj)
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


_PARTNER_GRAPH_MAX_DEPTH = 5


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
        sid = _strict_partner_sim_id(t)
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
    sis: typing.List[SuperInteraction] = []
    try:
        for si in sim.si_state.sis_actor_gen():
            sis.append(si)
    except Exception:
        pass
    try:
        queue = sim.queue
        if queue is not None:
            for si in queue:
                sis.append(si)
    except Exception:
        pass
    return sis


def _social_partner_sim_ids(sim: Sim, self_sim_id: int) -> typing.List[int]:
    """Other Sims reachable from explicit social-ish SI participant state."""
    uniq: typing.Set[int] = set()
    try:
        for si in _all_super_interactions_on_sim(sim):
            uniq |= _partner_ids_from_super_interaction(si, self_sim_id)
    except Exception:
        pass
    return sorted(uniq)


# ---------------------------------------------------------------------------
# Exhaustive SuperInteraction dumps (development profile only by default).
# Sends large ``logs`` payloads each tick — watch HTTP timeout/size if ticks fail.

_VERBOSE_DUMP_LOG_CAPACITY = False


def verbose_si_dump_enabled() -> bool:
    return VERBOSE_SIM_INTERACTION_DUMP


def _ensure_verbose_dump_log_capacity() -> None:
    global _VERBOSE_DUMP_LOG_CAPACITY
    if not VERBOSE_SIM_INTERACTION_DUMP or _VERBOSE_DUMP_LOG_CAPACITY:
        return
    set_max_log_buffer(LOG_STAGING_MAX)
    _VERBOSE_DUMP_LOG_CAPACITY = True


_ATTR_REPR_SOFT = 520
_DUMP_SOFT_PAYLOAD = 7500
_MAX_DUMP_PARTS_PER_ACTOR = 480
_MAX_DUMP_CHARS_PER_ACTOR = 800_000


def _squash_repr(val: typing.Any, soft: int = _ATTR_REPR_SOFT) -> str:
    try:
        if isinstance(val, SimInfo):
            return "SimInfo(id=%s cls=%s)" % (val.id, val.__class__.__name__)
        if isinstance(val, Sim):
            sid = getattr(val, "id", "?")
            return "Sim(id=%s cls=%s)" % (sid, val.__class__.__name__)
        if isinstance(val, SuperInteraction):
            return "SuperInteraction(cls=%s id=%s pyid=%s)" % (
                val.__class__.__name__,
                getattr(val, "id", "?"),
                id(val),
            )
        if isinstance(val, dict):
            if len(val) <= 18:
                s = repr(val)
            else:
                ks = ",".join(repr(k) for k in list(val.keys())[:42])
                s = "{dict len=%s keys=%s}" % (len(val), ks[: soft - 26])
        elif isinstance(val, (frozenset, set, tuple, list)):
            s = "%s[len=%s] %s" % (
                type(val).__name__,
                len(val),
                repr(tuple(val)[:12])[: soft - 32],
            )
        else:
            s = repr(val)
    except Exception as exc:
        return "<reprfail %s>" % (exc,)
    if len(s) <= soft:
        return s
    return "%s…[%s chars]" % (s[:soft], len(s))


def _lines_for_super_interaction(
    si: SuperInteraction, where: str, seq: int
) -> typing.Iterator[str]:
    cls = si.__class__.__name__
    si_ea_id = getattr(si, "id", "?")
    yield "%%% where={} seq={} class={} si.id={} pyid={}".format(
        where,
        seq,
        cls,
        si_ea_id,
        id(si),
    )
    try:
        names = sorted(dir(si))
    except Exception as exc:
        yield "### dir(si) failed: %s" % (exc,)
        return

    for name in names:
        if name.startswith("__") and name.endswith("__"):
            continue
        try:
            val = getattr(si, name)
        except Exception as exc:
            yield "%s=<getter %s>" % (name, exc)
            continue
        try:
            if callable(val):
                qn = getattr(val, "__qualname__", None) or getattr(val, "__name__", "?")
                yield "%s=<callable %s>" % (name, qn)
                continue
        except Exception:
            pass
        try:
            txt = _squash_repr(val)
        except Exception as exc:
            yield "%s=<squashfail %s>" % (name, exc)
            continue
        yield "%s=%s" % (name, txt)


def _verbose_si_dump_for_actor(
    sim_info: SimInfo,
    sim: Sim,
    social_partner_ids: typing.Sequence[int],
) -> None:
    _ensure_verbose_dump_log_capacity()

    actor = "%s|%s|%s" % (
        str(sim_info.id),
        str(sim_info.first_name),
        str(sim_info.last_name),
    )
    log_debug(
        "SI_DUMP",
        "[%s] prelude social_partner_sim_ids=%s — dir() sweep"
        % (actor, list(social_partner_ids)),
    )

    sis_labeled: typing.List[typing.Tuple[str, SuperInteraction]] = []
    try:
        for i, si in enumerate(sim.si_state.sis_actor_gen()):
            if isinstance(si, SuperInteraction):
                sis_labeled.append(("run|%s" % i, si))
    except Exception as exc:
        log_debug("SI_DUMP", "[%s] run_iterate_failed=%s" % (actor, exc))

    try:
        queue = sim.queue
        if queue is not None:
            for i, si in enumerate(queue):
                if isinstance(si, SuperInteraction):
                    sis_labeled.append(("q|%s" % i, si))
    except Exception as exc:
        log_debug("SI_DUMP", "[%s] queue_iterate_failed=%s" % (actor, exc))

    parts = 0
    chars_budget = 0
    aborted_reason = ""

    slab: typing.List[str] = []
    slab_chars = 0

    def flush_slab(note: str) -> None:
        nonlocal slab, slab_chars, parts, chars_budget, aborted_reason
        if aborted_reason:
            slab = []
            slab_chars = 0
            return
        if not slab:
            return
        blob = "\n".join(slab)
        parts += 1
        chars_budget += len(blob)
        log_debug(
            "SI_DUMP",
            "[%s] part=%s %s chars_budget=%s |%s"
            % (
                actor,
                parts,
                note,
                chars_budget,
                blob,
            ),
        )
        slab = []
        slab_chars = 0
        if parts >= _MAX_DUMP_PARTS_PER_ACTOR:
            aborted_reason = "payload_part_cap"
        elif chars_budget >= _MAX_DUMP_CHARS_PER_ACTOR:
            aborted_reason = "char_cap"

    for seq, (where, si) in enumerate(sis_labeled):
        if aborted_reason:
            break
        for ln in _lines_for_super_interaction(si, where, seq):
            if aborted_reason:
                break
            ln_len = len(ln) + 1
            if slab and slab_chars + ln_len > _DUMP_SOFT_PAYLOAD:
                flush_slab("chunk")
                if aborted_reason:
                    break
            slab.append(ln)
            slab_chars += ln_len
        if aborted_reason:
            break

    flush_slab("tail")

    if aborted_reason:
        log_debug(
            "SI_DUMP",
            "[%s] TRUNCATED reason=%s parts=%s ~chars=%s"
            % (actor, aborted_reason, parts, chars_budget),
        )


# Affordance-class multiset: sorted (class __name__, count) pairs from a sim's SI state.
ClassMultiset = typing.Tuple[typing.Tuple[str, int], ...]
SimFingerprintRow = typing.Tuple[int, ClassMultiset, ClassMultiset]
# Sorted (sim_id → sorted partner ids) wired to the viewer (SI graph + shared object cohort).
PartnerWireFingerprint = typing.Tuple[typing.Tuple[int, typing.Tuple[int, ...]], ...]
WorldFingerprint = typing.Tuple[
    typing.Optional[int],
    typing.Optional[int],
    typing.Tuple[SimFingerprintRow, ...],
    PartnerWireFingerprint,
]


def get_instanced_sim_infos() -> typing.List[SimInfo]:
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


def serialize_sim(sim_info: SimInfo) -> SerializedSim:
    """Convert a SimInfo into a structured snapshot for the bridge."""
    sid = int(sim_info.id)
    running: typing.List[RunningInteraction] = []
    queued: typing.List[QueuedInteraction] = []
    social_partners: typing.List[int] = []

    try:
        sim = sim_info.get_sim_instance()
        if sim is not None:
            running, queued = _interactions_for_sim(sim)
            social_partners = _social_partner_sim_ids(sim, sid)
            if VERBOSE_SIM_INTERACTION_DUMP:
                try:
                    _verbose_si_dump_for_actor(sim_info, sim, social_partners)
                except Exception:
                    pass
    except Exception:
        pass

    return SerializedSim(
        sim_id=sid,
        sim_id_str=str(sim_info.id),
        first_name=str(sim_info.first_name),
        last_name=str(sim_info.last_name),
        age=sim_info.age.name if sim_info.age is not None else None,
        gender=sim_info.gender.name if sim_info.gender is not None else None,
        is_npc=bool(sim_info.is_npc),
        household_id=(
            int(sim_info.household_id) if sim_info.household_id is not None else None
        ),
        zone_id=int(sim_info.zone_id) if sim_info.zone_id is not None else None,
        interactions_running=running,
        interactions_queue=queued,
        social_partner_sim_ids=social_partners,
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


def _iter_running_and_queued_super_interactions(
    sim: Sim,
) -> typing.Iterable[SuperInteraction]:
    try:
        for si in sim.si_state.sis_actor_gen():
            yield si
    except Exception:
        pass
    try:
        q = sim.queue
        if q is not None:
            for si in q:
                yield si
    except Exception:
        pass


def _activity_object_id_from_si(si: SuperInteraction) -> typing.Optional[int]:
    """
    Object id for **shared prop** activities (arcade, trivia box, group craft, etc.): any
    non-background SI whose ``target`` is not a Sim. No per-game class allowlist.
    """
    try:
        cn = si.__class__.__name__
    except Exception:
        return None
    if _si_class_excluded_from_activity_object_merge(cn):
        return None
    t = getattr(si, "target", None)
    if t is None or _strict_partner_sim_id(t) is not None:
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
    for si in _iter_running_and_queued_super_interactions(sim):
        oid = _activity_object_id_from_si(si)
        if oid is not None:
            oids.add(oid)
    return oids


def _partner_graph_instanced_wire() -> typing.Dict[int, typing.Set[int]]:
    """
    Canonical partner sets for serialized/wire Sims: SI-derived ``_social_partner_sim_ids``
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
        raw = _social_partner_sim_ids(sim, sid)
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


def _merge_shared_activity_object_partners_into_sims(
    sims: typing.List[SerializedSim],
) -> None:
    merged = _partner_graph_instanced_wire()
    lookup = {int(s.sim_id): s for s in sims}
    for sid, row in lookup.items():
        row.social_partner_sim_ids = sorted(merged.get(sid, set()))


def get_world_state() -> WorldState:
    """Collect full world snapshot: all instanced Sims + zone/lot context."""
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

    sims: typing.List[SerializedSim] = []
    for sim_info in get_instanced_sim_infos():
        try:
            sims.append(serialize_sim(sim_info))
        except Exception:
            pass

    _merge_shared_activity_object_partners_into_sims(sims)

    return WorldState(lot_id=lot_id, zone_id=zone_id, sims=sims)


def _serialize_running_interaction(si: SuperInteraction) -> RunningInteraction:
    """Minimal snapshot for the viewer (and future cancel by id)."""
    return RunningInteraction(
        interaction_id=int(si.id),
        interaction_id_str=str(si.id),
        class_name=si.__class__.__name__,
    )


def _interactions_for_sim(
    sim: Sim,
) -> typing.Tuple[
    typing.List[RunningInteraction],
    typing.List[QueuedInteraction],
]:
    """What the sim is running now vs what is queued (per EA interaction_commands patterns)."""
    running: typing.List[RunningInteraction] = []
    queued: typing.List[QueuedInteraction] = []

    try:
        for si in sim.si_state.sis_actor_gen():
            running.append(_serialize_running_interaction(si))
    except Exception:
        pass

    try:
        queue = sim.queue
        if queue is not None:
            head = getattr(queue, "running", None)
            for si in queue:
                base = _serialize_running_interaction(si)
                queued.append(
                    QueuedInteraction(
                        interaction_id=base.interaction_id,
                        interaction_id_str=base.interaction_id_str,
                        class_name=base.class_name,
                        is_queue_head=bool(head is not None and si is head),
                    )
                )
    except Exception:
        pass

    return running, queued


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
                if not _si_class_is_background_noise(name):
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
                    if not _si_class_is_background_noise(name):
                        q_c[name] += 1
                except Exception:
                    pass
    except Exception:
        pass
    q_tup = tuple(sorted(q_c.items()))

    return (run_tup, q_tup)
