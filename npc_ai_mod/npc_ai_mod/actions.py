"""
actions.py — apply AI decisions to Sims in the active zone.

Add new AI actions by:
  1. Implementing an ``apply_<action>(sim_info)`` function below.
  2. Registering it in ``_ACTION_HANDLERS``.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .logutil import log_error, log_info

if TYPE_CHECKING:
    from sims.sim_info import SimInfo

__all__ = ("apply_decisions",)


# ---------------------------------------------------------------------------
# Sim lookup
# ---------------------------------------------------------------------------


def _find_sim_info(sim_id: int) -> "Optional[SimInfo]":
    import services

    manager = services.sim_info_manager()
    if manager is None:
        return None
    return manager.get(sim_id)


# ---------------------------------------------------------------------------
# Individual action handlers
# ---------------------------------------------------------------------------


def _apply_go_home(sim_info: "SimInfo") -> None:
    try:
        from interactions.context import (
            InteractionContext,
            InteractionSource,
            QueueInsertStrategy,
        )
        from interactions.priority import Priority

        sim = sim_info.get_sim_instance()
        if sim is None:
            log_info(
                "actions.apply_go_home",
                f"sim {sim_info.sim_id} is not instanced, skipping",
            )
            return
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
    except Exception as exc:
        log_error("actions.apply_go_home", "failed to push go_home", exc)


# ---------------------------------------------------------------------------
# Dispatch table — add new actions here
# ---------------------------------------------------------------------------

_ACTION_HANDLERS: "Dict[str, Any]" = {
    "go_home": _apply_go_home,
}


# ---------------------------------------------------------------------------
# Public entry point called by Director
# ---------------------------------------------------------------------------


def apply_decisions(decisions: "List[Dict[str, Any]]") -> None:
    for decision in decisions:
        try:
            action = decision.get("action")
            sim_id = decision.get("sim_id")
            if not action or sim_id is None:
                continue
            sim_info = _find_sim_info(int(str(sim_id)))
            if sim_info is None:
                log_info(
                    "actions.apply_decisions",
                    f"sim_id={sim_id} not found in manager",
                )
                continue
            handler = _ACTION_HANDLERS.get(action)
            if handler is None:
                log_error(
                    "actions.apply_decisions",
                    f"unknown action {action!r} for sim_id={sim_id}",
                )
                continue
            handler(sim_info)
        except Exception as exc:
            log_error(
                "actions.apply_decisions", f"error applying {decision!r}", exc
            )
