"""Small helpers split out of ``director`` to keep orchestration readable."""

from __future__ import annotations

import typing

import alarms
from alarms import AlarmHandle
from clock import interval_in_real_seconds

from .logutil import log_error
from .sim_state.types_defs import WorldFingerprint


class ManagedAlarm:
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
            log_error(f"ManagedAlarm({tag})", "failed to register alarm", exc)

    def cancel(self) -> None:
        if self._handle is not None:
            try:
                alarms.cancel_alarm(self._handle)
            except Exception:
                pass
            self._handle = None


def fingerprint_diff(
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
