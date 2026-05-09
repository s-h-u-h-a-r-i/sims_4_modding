"""
sim_state.py — read and serialize NPC Sim data.

Responsible for collecting the current state of NPC Sims and returning it
as plain dicts suitable for JSON serialisation and sending to the AI service.
"""

from typing import TYPE_CHECKING, Any

import services

if TYPE_CHECKING:
    from sims.sim_info import SimInfo


def get_npc_sim_infos() -> "list[SimInfo]":
    """Return SimInfo objects for all NPC Sims currently in the zone."""
    # TODO: filter to NPCs only (exclude player household)
    raise NotImplementedError


def serialize_sim(sim_info: "SimInfo") -> "dict[str, Any]":
    """Convert a SimInfo into a JSON-serialisable dict."""
    # TODO: include traits, motives, current interaction, location, etc.
    raise NotImplementedError


def get_world_state() -> "dict[str, Any]":
    """Collect full world snapshot: all NPCs + zone context."""
    # TODO: gather sim states, time of day, lot info
    raise NotImplementedError
