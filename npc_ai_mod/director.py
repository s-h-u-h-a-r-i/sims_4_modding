"""
director.py — orchestrate ticks and apply AI decisions to NPC Sims.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import alarms
from clock import interval_in_real_seconds

from . import bridge, sim_state, tick_throttle
from .logutil import log_error
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
        """Send a tick to the AI service if the wall-clock throttle allows."""
        if not tick_throttle.allow_send():
            return
        try:
            bridge.post_tick(self._build_payload())
        except Exception as exc:
            log_error(
                "Director.push_tick_if_due",
                "unexpected error building/sending tick",
                exc,
            )

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

    def apply_decisions(self, decisions: "List[Dict[str, Any]]") -> None:
        """Push a list of AI decisions onto the appropriate NPCs."""
        raise NotImplementedError

    def push_interaction(self, sim_info: "SimInfo", interaction_id: int) -> None:
        """Queue a specific interaction on a Sim by its affordance GUID."""
        raise NotImplementedError


director = Director()
