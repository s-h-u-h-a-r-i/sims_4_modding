"""Apply server decisions to Sims in the active zone."""

from __future__ import annotations

import typing

from ..logutil import log_error, log_info
from ..schemas import DecisionOutcome, ServerDecision
from .registry import ACTION_HANDLERS
from .sim_lookup import find_sim_info


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
            sim_info = find_sim_info(int(str(sim_id)))
            if sim_info is None:
                msg = f"sim_id={sim_id} not found in manager"
                log_info("actions.apply_decisions", msg)
                outcomes.append(
                    DecisionOutcome(
                        decision_id=decision_id, status="failure", reason=msg
                    )
                )
                continue
            handler = ACTION_HANDLERS.get(action)
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
