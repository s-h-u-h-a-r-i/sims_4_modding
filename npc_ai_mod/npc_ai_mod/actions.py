"""
actions.py — apply AI decisions to Sims in the active zone.

Add new AI actions by:
  1. Implementing an ``apply_<action>(sim_info)`` function below that returns
     ``(ok: bool, reason: str | None)``.
  2. Registering it in ``_ACTION_HANDLERS``.
"""

from __future__ import annotations

import typing

import services
from interactions.context import (
    InteractionContext,
    InteractionSource,
    QueueInsertStrategy,
)
from interactions.priority import Priority
from sims.sim_info import SimInfo

from .logutil import log_error, log_info
from .schemas import DecisionOutcome, ServerDecision

ActionHandler = typing.Callable[[SimInfo], typing.Tuple[bool, typing.Optional[str]]]


def apply_decisions(
    decisions: typing.Sequence[ServerDecision],
) -> typing.List[DecisionOutcome]:
    """Apply each decision and return outcomes for the next tick."""
    outcomes: typing.List[DecisionOutcome] = []
    for decision in decisions:
        decision_id = decision.decision_id
        action = decision.action
        sim_id = decision.sim_id

        if not action or sim_id is None or decision_id is None:
            continue

        try:
            sim_info = _find_sim_info(int(str(sim_id)))
            if sim_info is None:
                msg = f"sim_id={sim_id} not found in manager"
                log_info("actions.apply_decisions", msg)
                outcomes.append(
                    DecisionOutcome(
                        decision_id=decision_id, status="failure", reason=msg
                    )
                )
                continue
            handler = _ACTION_HANDLERS.get(action)
            if handler is None:
                msg = f"unknown action {action!r}"
                log_error("actions.apply_decisions", f"{msg} for sim_id={sim_id}")
                outcomes.append(
                    DecisionOutcome(
                        decision_id=decision_id, status="failure", reason=msg
                    )
                )
                continue
            ok, reason = handler(sim_info)
            outcomes.append(
                DecisionOutcome(
                    decision_id=decision_id,
                    status="success" if ok else "failure",
                    reason=reason,
                )
            )
        except Exception as exc:
            log_error(
                "actions.apply_decisions",
                f"error applying decision id={decision_id!r}",
                exc,
            )
            outcomes.append(
                DecisionOutcome(
                    decision_id=decision_id,
                    status="failure",
                    reason=str(exc),
                )
            )

    return outcomes


def _find_sim_info(sim_id: int) -> typing.Optional[SimInfo]:

    manager = services.sim_info_manager()
    if manager is None:
        return None
    return manager.get(sim_id)


def _apply_go_home(sim_info: SimInfo) -> typing.Tuple[bool, typing.Optional[str]]:
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
        # EnqueueResult.__bool__ checks both test_result and execute_result
        if result:
            return True, None
        return False, str(result)
    except Exception as exc:
        log_error("actions.apply_go_home", "failed to push go_home", exc)
        return False, str(exc)


_ACTION_HANDLERS: typing.Mapping[str, ActionHandler] = {
    "go_home": _apply_go_home,
}
