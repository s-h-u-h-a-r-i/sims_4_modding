"""Resolve ``SimInfo`` from the live EA manager."""

from __future__ import annotations

import typing

import services
from sims.sim_info import SimInfo

__all__ = ("find_sim_info",)


def find_sim_info(sim_id: int) -> typing.Optional[SimInfo]:
    manager = services.sim_info_manager()
    if manager is None:
        return None
    return manager.get(sim_id)
