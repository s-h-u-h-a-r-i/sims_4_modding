"""
director.py — orchestrate ticks and apply AI decisions to NPC Sims.
"""

from __future__ import annotations

import time
import typing
from dataclasses import replace

import alarms
from alarms import AlarmHandle
from clock import interval_in_real_seconds

from . import actions, bridge, config, sim_state
from .logutil import drain_logs_for_tick, log_debug, log_error, log_info
from .runtime import is_game_paused
from .schemas import DecisionOutcome, TickInfo, TickPayload
from .sim_state import WorldFingerprint
from .utils import iso_utc_now

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


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------


class Director:
    def __init__(self) -> None:
        self._tick_seq: int = 0
        self._probe_alarm = _ManagedAlarm()
        self._debounce_alarm = _ManagedAlarm()
        self._last_sent_fingerprint: typing.Optional[WorldFingerprint] = None
        self._pending_fingerprint: typing.Optional[WorldFingerprint] = None
        self._dirty_since: typing.Optional[float] = None
        self._consecutive_dirty_probes: int = 0
        self._consecutive_clean_probes: int = 0
        self._debug_unchanged_probe_streak: int = 0
        self._last_post_monotonic: typing.Optional[float] = None
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
        self._last_post_monotonic = None
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

    # ------------------------------------------------------------------
    # Probe callback
    # ------------------------------------------------------------------

    def _on_probe_fire(self, _handle: AlarmHandle) -> None:
        if is_game_paused():
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
            diff = _fingerprint_diff(self._last_sent_fingerprint, fp)
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

    def _on_debounce_fire(self, _handle: AlarmHandle) -> None:
        self._debounce_alarm.cancel()
        log_debug(
            "Director", "debounce timer fired: attempting POST after quiet period"
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
            tick=TickInfo(id=self._tick_seq, timestamp_utc=iso_utc_now()),
            world=sim_state.get_world_state(),
            outcomes=outcomes,
        )

    def _flush_tick(self, reason: typing.Optional[str] = None) -> None:
        if is_game_paused():
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

        self._debounce_alarm.cancel()

        try:
            payload = self._build_payload()
            logs_batch = drain_logs_for_tick(config.MOD_LOG_DRAIN_PER_TICK)
            if logs_batch:
                payload = replace(payload, logs=logs_batch)
            response = bridge.post_tick(payload)
            if response:
                self._dirty_since = None
                self._pending_fingerprint = None
                self._consecutive_dirty_probes = 0
                self._consecutive_clean_probes = 0
                self._debug_unchanged_probe_streak = 0
                self._last_post_monotonic = time.monotonic()
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
                        f"POST tick ({reason}): synced post-apply activity fingerprint "
                        f"(paired_match={synced is not None})",
                    )
        except Exception as exc:
            log_error(
                "Director._flush_tick",
                "unexpected error building/sending tick",
                exc,
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _ManagedAlarm:
    """Wraps a single Sims 4 real-time alarm handle with safe schedule/cancel."""

    def __init__(self) -> None:
        self._handle: typing.Optional[AlarmHandle] = None

    def schedule(
        self,
        owner: object,
        interval_s: float,
        callback: typing.Callable[[AlarmHandle], None],
        *,
        repeating: bool = False,
        tag: str = "alarm",
    ) -> None:
        self.cancel()
        try:
            self._handle = alarms.add_alarm_real_time(
                owner,
                interval_in_real_seconds(interval_s),
                callback,
                repeating=repeating,
                use_sleep_time=False,
            )
        except Exception as exc:
            log_error(f"_ManagedAlarm({tag})", "failed to register alarm", exc)

    def cancel(self) -> None:
        if self._handle is not None:
            try:
                alarms.cancel_alarm(self._handle)
            except Exception:
                pass
            self._handle = None


def _fingerprint_diff(
    old: typing.Optional[WorldFingerprint],
    new: typing.Optional[WorldFingerprint],
) -> str:
    """Human-readable delta between fingerprints — Director debug logging only."""
    if old is None:
        return "(no previous fingerprint)"
    if new is None:
        return "(new fingerprint is None)"
    old_sims = {row[0]: row for row in old[2]}
    new_sims = {row[0]: row for row in new[2]}
    parts: typing.List[str] = []
    if old[:2] != new[:2]:
        parts.append(f"zone/lot {old[:2]} → {new[:2]}")
    all_ids = sorted(set(old_sims) | set(new_sims))
    for sid in all_ids:
        o = old_sims.get(sid)
        n = new_sims.get(sid)
        if o is None:
            parts.append(f"sim {sid} appeared")
        elif n is None:
            parts.append(f"sim {sid} left")
        else:
            o_run, o_q = o[1], o[2]
            n_run, n_q = n[1], n[2]
            if o_run != n_run:
                parts.append(f"sim {sid} running {dict(o_run)} → {dict(n_run)}")
            if o_q != n_q:
                parts.append(f"sim {sid} queued {dict(o_q)} → {dict(n_q)}")
    op = old[3] if len(old) >= 4 else ()
    np = new[3] if len(new) >= 4 else ()
    if op != np:
        parts.append("partner wire edges changed")
    return "; ".join(parts) if parts else "(no visible diff)"


director = Director()
