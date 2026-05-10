"""
director.py — orchestrate ticks and apply AI decisions to NPC Sims.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import alarms
from clock import interval_in_real_seconds

from . import bridge, sim_state, tick_throttle
from .logutil import log_error, log_info
from .utils import iso_utc_now

__all__ = ("director",)

if TYPE_CHECKING:
    from sims.sim_info import SimInfo

_REAL_SECONDS_BETWEEN_TICKS = 5


class Director:
    def __init__(self) -> None:
        self._tick_seq: int = 0
        self._alarm_handle: Optional[Any] = None

    def _build_payload(self) -> Dict[str, Any]:
        self._tick_seq += 1
        return {
            "tick": {"id": self._tick_seq, "timestamp_utc": iso_utc_now()},
            "world": sim_state.get_world_state(),
        }

    def push_tick_if_due(self) -> None:
        """Send a tick to the AI service if the wall-clock throttle allows and game is not paused."""
        if sim_state.is_game_paused():
            return
        if not tick_throttle.allow_send():
            return
        try:
            response = bridge.post_tick(self._build_payload())
            if response:
                decisions = response.get("decisions") or []
                if decisions:
                    log_info("Director", f"received {len(decisions)} decision(s): {decisions}")
                    self.apply_decisions(decisions)
        except Exception as exc:
            log_error(
                "Director.push_tick_if_due",
                "unexpected error building/sending tick",
                exc,
            )

    def apply_decisions(self, decisions: "List[Dict[str, Any]]") -> None:
        for decision in decisions:
            try:
                action = decision.get("action")
                sim_id = decision.get("sim_id")
                if not action or sim_id is None:
                    continue
                sim_info = self._find_sim_info(int(str(sim_id)))
                if sim_info is None:
                    log_info("Director.apply_decisions", f"sim_id={sim_id} not found in manager")
                    continue
                if action == "go_home":
                    self._apply_go_home(sim_info)
                else:
                    log_error(
                        "Director.apply_decisions",
                        f"unknown action {action!r} for sim_id={sim_id}",
                    )
            except Exception as exc:
                log_error("Director.apply_decisions", f"error applying {decision!r}", exc)

    def _on_alarm_fire(self, _handle: Any) -> None:
        self.push_tick_if_due()

    def _cancel_alarm(self) -> None:
        if self._alarm_handle is not None:
            try:
                alarms.cancel_alarm(self._alarm_handle)
            except Exception:
                pass
            self._alarm_handle = None

    def _register_alarm(self) -> None:
        self._cancel_alarm()
        try:
            self._alarm_handle = alarms.add_alarm_real_time(
                self,
                interval_in_real_seconds(_REAL_SECONDS_BETWEEN_TICKS),
                self._on_alarm_fire,
                repeating=True,
                use_sleep_time=False,
            )
        except Exception as exc:
            log_error(
                "Director._register_alarm", "failed to register recurring alarm", exc
            )

    def on_zone_loaded(self) -> None:
        """Called once when the venue finishes loading. Sends first tick and starts recurring alarm."""
        self._register_alarm()
        self.push_tick_if_due()

    def on_zone_unloaded(self) -> None:
        """Called when leaving a zone; cancels the recurring alarm."""
        self._cancel_alarm()

    def _find_sim_info(self, sim_id: int) -> "Optional[SimInfo]":
        import services
        manager = services.sim_info_manager()
        if manager is None:
            return None
        return manager.get(sim_id)

    def _apply_go_home(self, sim_info: "SimInfo") -> None:
        try:
            from interactions.context import InteractionContext, InteractionSource, QueueInsertStrategy
            from interactions.priority import Priority

            sim = sim_info.get_sim_instance()
            if sim is None:
                log_info("Director._apply_go_home", f"sim {sim_info.sim_id} is not instanced, skipping")
                return
            go_home_affordance = sim_info.SIM_SKEWER_AFFORDANCES[0]
            context = InteractionContext(
                sim,
                InteractionSource.SCRIPT,
                Priority.High,
                insert_strategy=QueueInsertStrategy.NEXT,
            )
            result = sim.push_super_affordance(go_home_affordance, None, context)
            log_info("Director._apply_go_home", f"push_super_affordance({sim_info.first_name} {sim_info.last_name}) -> {result}")
        except Exception as exc:
            log_error("Director._apply_go_home", "failed to push go_home", exc)


director = Director()
