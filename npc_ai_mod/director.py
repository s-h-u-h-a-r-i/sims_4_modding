"""
director.py — apply AI decisions to NPC Sims.

Receives decisions from bridge.py and pushes the corresponding Sims 4
interactions / behaviour changes onto the target Sims.
"""
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sims.sim_info import SimInfo


def on_zone_loaded() -> None:
    """
    Called once per save-load (from hooks.py).
    Kick off the first state snapshot + decision cycle.
    """
    # TODO: call sim_state.get_world_state(), bridge.send_state(), then apply
    raise NotImplementedError


def apply_decisions(decisions: "list[dict[str, Any]]") -> None:
    """Push a list of AI decisions onto the appropriate NPCs."""
    # TODO: route each decision to the right Sim and interaction
    raise NotImplementedError


def push_interaction(sim_info: "SimInfo", interaction_id: int) -> None:
    """Queue a specific interaction on a Sim by its affordance GUID."""
    # TODO: use InteractionContext + affordance_manager to push the interaction
    raise NotImplementedError
