from __future__ import annotations

import typing

from interactions.context import (
    InteractionContext,
    InteractionSource,
    QueueInsertStrategy,
)
from interactions.priority import Priority
from sims.sim_info import SimInfo

from ...logutil import log_error, log_info

__all__ = ("apply_go_home",)


def apply_go_home(sim_info: SimInfo) -> typing.Tuple[bool, typing.Optional[str]]:
    try:
        sim = sim_info.get_sim_instance()
        if sim is None:
            msg = f"sim {sim_info.sim_id} is not instanced"
            log_info("actions.apply_go_home", f"{msg}, skipping")
            return False, msg
        go_home_affordance = sim_info.SIM_SKEWER_AFFORDANCES[0]
        context = InteractionContext(
            sim,
            InteractionSource.SCRIPT,
            Priority.High,
            insert_strategy=QueueInsertStrategy.NEXT,
        )
        result = sim.push_super_affordance(go_home_affordance, None, context)
        log_info(
            "actions.apply_go_home",
            f"push_super_affordance({sim_info.first_name} {sim_info.last_name}) -> {result}",
        )
        if result:
            return True, None
        return False, str(result)
    except Exception as exc:
        log_error("actions.apply_go_home", "failed to push go_home", exc)
        return False, str(exc)
