"""
Exhaustive SuperInteraction dumps (development profile only by default).
Sends large ``logs`` payloads each tick — watch bridge timeout/size if ticks fail.
"""

from __future__ import annotations

import typing

from interactions.base.super_interaction import SuperInteraction
from sims.sim import Sim
from sims.sim_info import SimInfo

from ..config import LOG_STAGING_MAX, VERBOSE_SIM_INTERACTION_DUMP
from ..logutil import log_debug, set_max_log_buffer

__all__ = ("verbose_si_dump_for_actor",)

_VERBOSE_DUMP_LOG_CAPACITY = False

_ATTR_REPR_SOFT = 520
_DUMP_SOFT_PAYLOAD = 7500
_MAX_DUMP_PARTS_PER_ACTOR = 480
_MAX_DUMP_CHARS_PER_ACTOR = 800_000


def verbose_si_dump_for_actor(
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


def _ensure_verbose_dump_log_capacity() -> None:
    global _VERBOSE_DUMP_LOG_CAPACITY
    if not VERBOSE_SIM_INTERACTION_DUMP or _VERBOSE_DUMP_LOG_CAPACITY:
        return
    set_max_log_buffer(LOG_STAGING_MAX)
    _VERBOSE_DUMP_LOG_CAPACITY = True


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
