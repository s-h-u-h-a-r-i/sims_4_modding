"""
director.py — orchestrate ticks and apply AI decisions to NPC Sims.
"""

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import alarms
from clock import interval_in_real_seconds

from . import bridge, sim_state
from .logutil import log_debug, log_error, log_info
from .utils import iso_utc_now

__all__ = ("director",)

if TYPE_CHECKING:
    from sims.sim_info import SimInfo

# How often we compare fingerprints (game activity probe, real wall clock).
_PROBE_REAL_SECONDS = 0.75
# After the world stops changing, wait this long before sending one tick (coalesce bursts).
_DEBOUNCE_REAL_SECONDS = 0.35
# Require this many consecutive dirty probes before arming debounce.
_DIRTY_CONFIRM_PROBES = 2
# Require this many consecutive clean probes before resetting the dirty counter.
# Prevents alternating clean/dirty oscillation from keeping dirty_count stuck at 1.
_CLEAN_CONFIRM_TO_RESET = 2
# If the world never goes quiet (constant churn), force a tick at least this often.
_MAX_WAIT_DIRTY_REAL_SECONDS = 4.0
# Force a tick even when the world looks stable (fingerprint unchanged).
# This is the maximum time a viewer command (e.g. "go home") can sit undelivered
# when no gameplay event naturally triggers a POST first.
_MAX_IDLE_POST_REAL_SECONDS = 5.0


# Minimum real time between HTTP ticks (debounce/max_wait still schedule, but POST waits).
# Stops POST ↔ immediate "dirty" ↔ POST tight loops when paired reads disagree with last_sent.
_MIN_POST_INTERVAL_REAL_S = 1.25


class Director:
    def __init__(self) -> None:
        self._tick_seq: int = 0
        self._probe_handle: Optional[Any] = None
        self._debounce_handle: Optional[Any] = None
        self._last_sent_fingerprint: Optional[tuple] = None
        self._pending_fingerprint: Optional[tuple] = None
        self._dirty_since: Optional[float] = None
        self._consecutive_dirty_probes: int = 0
        self._consecutive_clean_probes: int = 0
        self._debug_unchanged_probe_streak: int = 0
        self._last_post_monotonic: Optional[float] = None

    def _activity_fp(self) -> tuple:
        """Prefer paired stable reads; fall back to a single sample for zone_load / edge cases."""
        fp = sim_state.world_activity_fingerprint_if_stable()
        if fp is not None:
            return fp
        return sim_state.world_activity_fingerprint()

    def _build_payload(self) -> Dict[str, Any]:
        self._tick_seq += 1
        return {
            "tick": {"id": self._tick_seq, "timestamp_utc": iso_utc_now()},
            "world": sim_state.get_world_state(),
        }

    def push_tick_if_due(self) -> None:
        """Manual / compatibility entry point: send if the world differs from the last successful tick."""
        self._flush_tick("manual")

    def _flush_tick(self, reason: Optional[str] = None) -> None:
        if sim_state.is_game_paused():
            return
        now = time.monotonic()
        fp = self._activity_fp()
        if fp == self._last_sent_fingerprint:
            self._dirty_since = None
            self._pending_fingerprint = None
            if reason:
                log_debug(
                    "Director",
                    f"skip POST: fingerprint unchanged vs last successful tick (reason={reason!r})",
                )
            return

        if (
            reason not in ("zone_load", "manual", "max_wait", "idle_keepalive")
            and self._last_post_monotonic is not None
            and now - self._last_post_monotonic < _MIN_POST_INTERVAL_REAL_S
        ):
            log_debug(
                "Director",
                f"POST cooldown ({_MIN_POST_INTERVAL_REAL_S}s): deferring (reason={reason!r})",
            )
            return

        self._cancel_debounce_alarm()

        try:
            response = bridge.post_tick(self._build_payload())
            if response:
                self._dirty_since = None
                self._pending_fingerprint = None
                self._consecutive_dirty_probes = 0
                self._consecutive_clean_probes = 0
                self._debug_unchanged_probe_streak = 0
                self._last_post_monotonic = time.monotonic()
                decisions = response.get("decisions") or []
                if decisions:
                    log_info(
                        "Director",
                        f"received {len(decisions)} decision(s): {decisions}",
                    )
                    self.apply_decisions(decisions)
                synced = sim_state.world_activity_fingerprint_if_stable()
                self._last_sent_fingerprint = synced or sim_state.world_activity_fingerprint()
                if reason:
                    log_debug(
                        "Director",
                        f"POST tick ({reason}): synced post-apply activity fingerprint "
                        f"(paired_match={synced is not None})",
                    )
        except Exception as exc:
            log_error(
                "Director._flush_tick",
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
                    log_info(
                        "Director.apply_decisions",
                        f"sim_id={sim_id} not found in manager",
                    )
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

    def _on_probe_fire(self, _handle: Any) -> None:
        if sim_state.is_game_paused():
            return
        fp = sim_state.world_activity_fingerprint_if_stable()
        if fp is None:
            log_debug(
                "Director.probe",
                "paired activity fingerprints disagree this sample; skipping (no dirty/clean)",
            )
            return
        if fp == self._last_sent_fingerprint:
            self._consecutive_clean_probes += 1
            self._debug_unchanged_probe_streak += 1
            now = time.monotonic()
            if (
                self._last_post_monotonic is not None
                and now - self._last_post_monotonic >= _MAX_IDLE_POST_REAL_SECONDS
            ):
                log_debug(
                    "Director.probe",
                    f"idle keepalive: {_MAX_IDLE_POST_REAL_SECONDS}s since last POST "
                    "(flushing any queued viewer commands)",
                )
                self._flush_tick("idle_keepalive")
                return
            log_debug(
                "Director.probe",
                "no world fingerprint delta vs last successful tick (same as last POST); "
                f"unchanged_probe_streak={self._debug_unchanged_probe_streak}",
            )
            if self._consecutive_clean_probes >= _CLEAN_CONFIRM_TO_RESET:
                self._consecutive_dirty_probes = 0
                self._dirty_since = None
                self._pending_fingerprint = None
                self._cancel_debounce_alarm()
            return

        self._consecutive_clean_probes = 0
        self._consecutive_dirty_probes += 1
        if self._consecutive_dirty_probes == 1:
            self._dirty_since = time.monotonic()

        now = time.monotonic()
        confirmed = self._consecutive_dirty_probes >= _DIRTY_CONFIRM_PROBES

        if not confirmed:
            log_debug(
                "Director.probe",
                "tentative dirty probe "
                f"{self._consecutive_dirty_probes}/{_DIRTY_CONFIRM_PROBES} "
                "(await confirmation — suppresses single-frame fingerprint flutter)",
            )
            return

        if fp != self._pending_fingerprint:
            self._pending_fingerprint = fp
            if self._dirty_since is None:
                self._dirty_since = now
            self._schedule_debounce_flush()
            diff = sim_state.fingerprint_diff(self._last_sent_fingerprint, fp)
            log_debug(
                "Director.probe",
                "world dirty vs last tick: scheduled debounced POST "
                f"({_DEBOUNCE_REAL_SECONDS}s quiet) or max_wait {_MAX_WAIT_DIRTY_REAL_SECONDS}s"
                f" | diff: {diff}",
            )

        if (
            self._dirty_since is not None
            and now - self._dirty_since >= _MAX_WAIT_DIRTY_REAL_SECONDS
        ):
            log_debug(
                "Director",
                "max_wait: forcing POST (fingerprint still changing over "
                f"{_MAX_WAIT_DIRTY_REAL_SECONDS}s)",
            )
            self._flush_tick("max_wait")

    def _on_debounce_fire(self, _handle: Any) -> None:
        self._debounce_handle = None
        log_debug(
            "Director",
            "debounce timer fired: attempting POST after quiet period",
        )
        self._flush_tick("debounce")

    def _schedule_debounce_flush(self) -> None:
        self._cancel_debounce_alarm()
        try:
            self._debounce_handle = alarms.add_alarm_real_time(
                self,
                interval_in_real_seconds(_DEBOUNCE_REAL_SECONDS),
                self._on_debounce_fire,
                repeating=False,
                use_sleep_time=False,
            )
        except Exception as exc:
            log_error(
                "Director._schedule_debounce_flush",
                "failed to register debounce alarm",
                exc,
            )

    def _cancel_debounce_alarm(self) -> None:
        if self._debounce_handle is not None:
            try:
                alarms.cancel_alarm(self._debounce_handle)
            except Exception:
                pass
            self._debounce_handle = None

    def _cancel_probe_alarm(self) -> None:
        if self._probe_handle is not None:
            try:
                alarms.cancel_alarm(self._probe_handle)
            except Exception:
                pass
            self._probe_handle = None

    def _register_probe_alarm(self) -> None:
        self._cancel_probe_alarm()
        try:
            self._probe_handle = alarms.add_alarm_real_time(
                self,
                interval_in_real_seconds(_PROBE_REAL_SECONDS),
                self._on_probe_fire,
                repeating=True,
                use_sleep_time=False,
            )
        except Exception as exc:
            log_error(
                "Director._register_probe_alarm",
                "failed to register probe alarm",
                exc,
            )

    def on_zone_loaded(self) -> None:
        """Called once when the venue finishes loading."""
        self._last_sent_fingerprint = None
        self._dirty_since = None
        self._pending_fingerprint = None
        self._consecutive_dirty_probes = 0
        self._consecutive_clean_probes = 0
        self._debug_unchanged_probe_streak = 0
        self._last_post_monotonic = None
        self._register_probe_alarm()
        self._flush_tick("zone_load")

    def on_zone_unloaded(self) -> None:
        """Called when leaving a zone."""
        self._cancel_probe_alarm()
        self._cancel_debounce_alarm()

    def _find_sim_info(self, sim_id: int) -> "Optional[SimInfo]":
        import services

        manager = services.sim_info_manager()
        if manager is None:
            return None
        return manager.get(sim_id)

    def _apply_go_home(self, sim_info: "SimInfo") -> None:
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
                    "Director._apply_go_home",
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
                "Director._apply_go_home",
                f"push_super_affordance({sim_info.first_name} {sim_info.last_name}) -> {result}",
            )
        except Exception as exc:
            log_error("Director._apply_go_home", "failed to push go_home", exc)


director = Director()
