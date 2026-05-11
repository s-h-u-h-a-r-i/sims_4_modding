"""
Build-selected settings for the mod.

``generated.py`` is produced by ``build.py`` / ``scripts/build.py`` from
``profiles/<profile>.py``. If missing (fresh checkout without a build yet), imports
fallback to ``profiles/production.py``.
"""

from __future__ import annotations

try:
    from .generated import (
        LOG_STAGING_MAX,
        MOD_LOG_DRAIN_PER_TICK,
        PROFILE_NAME,
        VERBOSE_SIM_INTERACTION_DUMP,
    )
except ImportError:
    from .profiles import production as _p

    PROFILE_NAME = _p.PROFILE_NAME
    VERBOSE_SIM_INTERACTION_DUMP = _p.VERBOSE_SIM_INTERACTION_DUMP
    MOD_LOG_DRAIN_PER_TICK = _p.MOD_LOG_DRAIN_PER_TICK
    LOG_STAGING_MAX = _p.LOG_STAGING_MAX

__all__ = (
    "PROFILE_NAME",
    "VERBOSE_SIM_INTERACTION_DUMP",
    "MOD_LOG_DRAIN_PER_TICK",
    "LOG_STAGING_MAX",
)
