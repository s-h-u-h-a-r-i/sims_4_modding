"""Map live SI queues to schema types."""

from __future__ import annotations

import typing

from interactions.base.super_interaction import SuperInteraction
from sims.sim import Sim

from ..schemas import QueuedInteraction, RunningInteraction


def _serialize_running_interaction(si: SuperInteraction) -> RunningInteraction:
    """Minimal snapshot for the viewer (and future cancel by id)."""
    return RunningInteraction(
        interaction_id=int(si.id),
        interaction_id_str=str(si.id),
        class_name=si.__class__.__name__,
    )


def interactions_for_sim(
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
