"""
director.py — orchestrate ticks and apply AI decisions to NPC Sims.
"""

from __future__ import annotations

import time
import typing
import uuid
from dataclasses import replace

from alarms import AlarmHandle

from . import actions, bridge, config, sim_state
from .director_support import ManagedAlarm, fingerprint_diff
from .logutil import drain_logs_for_tick, log_debug, log_error, log_info
from .schemas import DecisionOutcome, TickInfo, TickPayload
from .sim_state import WorldFingerprint
from .utils import iso_utc_now

__all__ = ("director",)

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
# when no gameplay event naturally triggers a bridge flush first.
_MAX_IDLE_TICK_REAL_SECONDS = 5.0

# Minimum real time between consecutive bridge round-trips (debounce/max_wait still arm, but send waits).
# Stops tick → immediate "dirty" → tick tight loops when paired reads disagree with last_sent.
_MIN_TICK_INTERVAL_REAL_S = 1.25


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------


class Director:
    def __init__(self) -> None:
        self._bridge_session_id: typing.Final[str] = str(uuid.uuid4())
        self._tick_seq: int = 0
        self._probe_alarm = ManagedAlarm()
        self._debounce_alarm = ManagedAlarm()
        self._last_sent_fingerprint: typing.Optional[WorldFingerprint] = None
        self._pending_fingerprint: typing.Optional[WorldFingerprint] = None
        self._dirty_since: typing.Optional[float] = None
        self._consecutive_dirty_probes: int = 0
        self._consecutive_clean_probes: int = 0
        self._debug_unchanged_probe_streak: int = 0
        self._last_tick_monotonic: typing.Optional[float] = None
        self._pending_outcomes: typing.List[DecisionOutcome] = []

    # ------------------------------------------------------------------
    # Zone lifecycle
    # ------------------------------------------------------------------

    def on_zone_loaded(self) -> None:
        """Called once when the venue finishes loading."""
        self._last_sent_fingerprint = None
        self._dirty_since = None
        self._pending_fingerprint = None
        self._consecutive_dirty_probes = 0
        self._consecutive_clean_probes = 0
        self._debug_unchanged_probe_streak = 0
        self._last_tick_monotonic = None
        self._probe_alarm.schedule(
            self,
            _PROBE_REAL_SECONDS,
            self._on_probe_fire,
            repeating=True,
            tag="probe",
        )
        self._flush_tick("zone_load")

    def on_zone_unloaded(self) -> None:
        """Called when leaving a zone."""
        self._probe_alarm.cancel()
        self._debounce_alarm.cancel()
        bridge.reset_persistent_connection()

    # ------------------------------------------------------------------
    # Probe callback
    # ------------------------------------------------------------------

    def _on_probe_fire(self, _handle: AlarmHandle) -> None:
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
                self._last_tick_monotonic is not None
                and now - self._last_tick_monotonic >= _MAX_IDLE_TICK_REAL_SECONDS
            ):
                log_debug(
                    "Director.probe",
                    f"idle keepalive: {_MAX_IDLE_TICK_REAL_SECONDS}s since last successful tick flush "
                    "(queued viewer commands)",
                )
                self._flush_tick("idle_keepalive")
                return
            log_debug(
                "Director.probe",
                "no world fingerprint delta vs last successful tick (same as last bridge round-trip); "
                f"unchanged_probe_streak={self._debug_unchanged_probe_streak}",
            )
            if self._consecutive_clean_probes >= _CLEAN_CONFIRM_TO_RESET:
                self._consecutive_dirty_probes = 0
                self._dirty_since = None
                self._pending_fingerprint = None
                self._debounce_alarm.cancel()
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
            self._debounce_alarm.schedule(
                self,
                _DEBOUNCE_REAL_SECONDS,
                self._on_debounce_fire,
                tag="debounce",
            )
            diff = fingerprint_diff(self._last_sent_fingerprint, fp)
            log_debug(
                "Director.probe",
                "world dirty vs last tick: scheduled debounced bridge flush "
                f"({_DEBOUNCE_REAL_SECONDS}s quiet) or max_wait {_MAX_WAIT_DIRTY_REAL_SECONDS}s"
                f" | diff: {diff}",
            )

        if (
            self._dirty_since is not None
            and now - self._dirty_since >= _MAX_WAIT_DIRTY_REAL_SECONDS
        ):
            log_debug(
                "Director",
                "max_wait: forcing bridge flush (fingerprint still changing over "
                f"{_MAX_WAIT_DIRTY_REAL_SECONDS}s)",
            )
            self._flush_tick("max_wait")

    def _on_debounce_fire(self, _handle: AlarmHandle) -> None:
        self._debounce_alarm.cancel()
        log_debug(
            "Director", "debounce timer fired: attempting tick flush after quiet period"
        )
        self._flush_tick("debounce")

    # ------------------------------------------------------------------
    # Tick flushing
    # ------------------------------------------------------------------

    def _activity_fp(self):
        """Prefer paired stable reads; fall back to a single sample for zone_load / edge cases."""
        fp = sim_state.world_activity_fingerprint_if_stable()
        if fp is not None:
            return fp
        return sim_state.world_activity_fingerprint()

    def _build_payload(self) -> TickPayload:
        self._tick_seq += 1
        outcomes = self._pending_outcomes
        self._pending_outcomes = []
        return TickPayload(
            tick=TickInfo(
                id=self._tick_seq,
                timestamp_utc=iso_utc_now(),
                bridge_session_id=self._bridge_session_id,
            ),
            world=sim_state.get_world_state(),
            outcomes=outcomes,
        )

    def _flush_tick(self, reason: typing.Optional[str] = None) -> None:
        now = time.monotonic()
        fp = self._activity_fp()
        if fp == self._last_sent_fingerprint:
            self._dirty_since = None
            self._pending_fingerprint = None
            if reason:
                log_debug(
                    "Director",
                    f"skip tick flush: fingerprint unchanged vs last successful tick (reason={reason!r})",
                )
            return

        if (
            reason not in ("zone_load", "manual", "max_wait", "idle_keepalive")
            and self._last_tick_monotonic is not None
            and now - self._last_tick_monotonic < _MIN_TICK_INTERVAL_REAL_S
        ):
            log_debug(
                "Director",
                f"tick interval cooldown ({_MIN_TICK_INTERVAL_REAL_S}s): deferring (reason={reason!r})",
            )
            return

        self._debounce_alarm.cancel()

        try:
            payload = self._build_payload()
            logs_batch = drain_logs_for_tick(config.MOD_LOG_DRAIN_PER_TICK)
            if logs_batch:
                payload = replace(payload, logs=logs_batch)
            response = bridge.exchange_tick(payload)
            if response:
                self._dirty_since = None
                self._pending_fingerprint = None
                self._consecutive_dirty_probes = 0
                self._consecutive_clean_probes = 0
                self._debug_unchanged_probe_streak = 0
                self._last_tick_monotonic = time.monotonic()
                decisions = response.decisions
                if decisions:
                    log_info(
                        "Director",
                        f"received {len(decisions)} decision(s): {decisions}",
                    )
                    outcomes = actions.apply_decisions(decisions)
                    if outcomes:
                        self._pending_outcomes.extend(outcomes)
                synced = sim_state.world_activity_fingerprint_if_stable()
                self._last_sent_fingerprint = (
                    synced or sim_state.world_activity_fingerprint()
                )
                if reason:
                    log_debug(
                        "Director",
                        f"tick flushed ({reason}): synced activity fingerprint after applying decisions "
                        f"(paired_match={synced is not None})",
                    )
        except Exception as exc:
            log_error(
                "Director._flush_tick",
                "unexpected error building/sending tick",
                exc,
            )


director = Director()
