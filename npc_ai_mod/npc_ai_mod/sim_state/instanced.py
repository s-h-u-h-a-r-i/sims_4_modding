"""Instanced Sim enumeration."""

from __future__ import annotations

import typing

import services
from sims.sim_info import SimInfo


def get_instanced_sim_infos() -> typing.List[SimInfo]:
    """Return SimInfo objects for all Sims currently instantiated in the zone."""
    manager = services.sim_info_manager()
    if manager is None:
        return []
    result = []
    for sim_info in manager.values():
        try:
            if sim_info.get_sim_instance() is not None:
                result.append(sim_info)
        except Exception:
            pass
    return result
