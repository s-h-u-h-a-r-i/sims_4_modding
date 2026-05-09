"""
director.py — apply AI decisions to NPC Sims.

Receives decisions from bridge.py and pushes the corresponding Sims 4
interactions / behaviour changes onto the target Sims.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict

from . import bridge

if TYPE_CHECKING:
    from sims.sim_info import SimInfo


def on_zone_loaded() -> None:
    payload: Dict[str, Any] = {
        "tick": {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        "world": {"lot_id": None, "zone_id": None, "sims": []},
    }
    bridge.post_tick(payload)


def apply_decisions(decisions: "list[dict[str, Any]]") -> None:
    """Push a list of AI decisions onto the appropriate NPCs."""
    # TODO: route each decision to the right Sim and interaction
    raise NotImplementedError


def push_interaction(sim_info: "SimInfo", interaction_id: int) -> None:
    """Queue a specific interaction on a Sim by its affordance GUID."""
    # TODO: use InteractionContext + affordance_manager to push the interaction
    raise NotImplementedError
