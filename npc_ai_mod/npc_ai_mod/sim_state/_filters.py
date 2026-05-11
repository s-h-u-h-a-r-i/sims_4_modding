"""Class-name filters for interaction fingerprints and shared-object merging."""

from __future__ import annotations

import typing

# Same sets used for activity fingerprints and shared-object cohort detection.
_FP_EXCLUDE_EXACT: frozenset[str] = frozenset(
    {
        "Emotion_Idle",
        "stand_Passive",
        "sit_Passive",
        "SocialPickerSI",  # social picker ticks ~1.5s as engine loop
    }
)
_FP_EXCLUDE_PREFIXES: typing.Tuple[str, ...] = (
    "Idle_",
    "idle_",
    "aggregate_",
    "reactions_",
)


def si_class_is_background_noise(class_name: str) -> bool:
    return class_name in _FP_EXCLUDE_EXACT or class_name.startswith(
        _FP_EXCLUDE_PREFIXES
    )


def si_class_excluded_from_activity_object_merge(class_name: str) -> bool:
    """Filter out locomotion/noise shells that often target non-Sim objects spuriously."""
    if si_class_is_background_noise(class_name):
        return True
    nl = class_name.lower()
    compact = nl.replace("-", "").replace("_", "")
    if "gohome" in compact:
        return True
    if nl.startswith("go_here") or nl.startswith("gohere"):
        return True
    if nl.startswith("routing"):
        return True
    if nl == "sim-stand":
        return True
    if (
        "leave_lot" in compact
        or "leavelot" in compact
        or compact.startswith("npc_leave")
    ):
        return True
    return False
