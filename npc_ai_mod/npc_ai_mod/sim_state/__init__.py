"""
Read and serialize NPC Sim data for the AI bridge.

Public API is re-exported here; implementation lives in submodules.
"""

from __future__ import annotations

from .fingerprints import (
    ClassMultiset,
    PartnerWireFingerprint,
    SimFingerprintRow,
    WorldFingerprint,
    world_activity_fingerprint,
    world_activity_fingerprint_if_stable,
)
from .instanced import get_instanced_sim_infos
from .partner_wire import partner_wire_fingerprint
from .snapshot import get_world_state, serialize_sim
from .verbose_si import verbose_si_dump_enabled

__all__ = (
    "ClassMultiset",
    "PartnerWireFingerprint",
    "SimFingerprintRow",
    "WorldFingerprint",
    "get_instanced_sim_infos",
    "get_world_state",
    "partner_wire_fingerprint",
    "serialize_sim",
    "verbose_si_dump_enabled",
    "world_activity_fingerprint",
    "world_activity_fingerprint_if_stable",
)
