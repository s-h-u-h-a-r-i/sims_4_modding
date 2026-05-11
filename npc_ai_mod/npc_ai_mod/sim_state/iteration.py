"""Iterate SuperInteractions attached to an instanced Sim (running + queue)."""

from __future__ import annotations

import typing

from interactions.base.super_interaction import SuperInteraction
from sims.sim import Sim

__all__ = ("iter_actor_and_queue_super_interactions",)


def iter_actor_and_queue_super_interactions(
    sim: Sim,
) -> typing.Iterator[SuperInteraction]:
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
