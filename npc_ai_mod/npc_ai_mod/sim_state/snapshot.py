"""Build ``SerializedSim`` / ``WorldState`` for the tick bridge (WebSocket JSON)."""

from __future__ import annotations

import typing

import services
from sims.sim_info import SimInfo

from ..config import VERBOSE_SIM_INTERACTION_DUMP
from ..schemas import QueuedInteraction, RunningInteraction, SerializedSim, WorldState
from .instanced import get_instanced_sim_infos
from .partner_wire import merge_shared_activity_object_partners_into_sims
from .partners import social_partner_sim_ids
from .serialized_interactions import interactions_for_sim
from .verbose_si import verbose_si_dump_for_actor

__all__ = ("get_world_state",)


def get_world_state() -> WorldState:
    """Collect full world snapshot: all instanced Sims + zone/lot context."""
    zone_id: typing.Optional[int] = None
    lot_id: typing.Optional[int] = None

    try:
        raw = services.current_zone_id()
        if raw is not None:
            zone_id = int(raw)
    except Exception:
        pass

    try:
        raw = services.active_lot_id()
        if raw is not None:
            lot_id = int(raw)
    except Exception:
        pass

    sims: typing.List[SerializedSim] = []
    for sim_info in get_instanced_sim_infos():
        try:
            sims.append(_serialize_sim(sim_info))
        except Exception:
            pass

    merge_shared_activity_object_partners_into_sims(sims)

    return WorldState(lot_id=lot_id, zone_id=zone_id, sims=sims)


def _serialize_sim(sim_info: SimInfo) -> SerializedSim:
    """Convert a SimInfo into a structured snapshot for the bridge."""
    sid = int(sim_info.id)
    running: typing.List[RunningInteraction] = []
    queued: typing.List[QueuedInteraction] = []
    social_partners: typing.List[int] = []

    try:
        sim = sim_info.get_sim_instance()
        if sim is not None:
            running, queued = interactions_for_sim(sim)
            social_partners = social_partner_sim_ids(sim, sid)
            if VERBOSE_SIM_INTERACTION_DUMP:
                try:
                    verbose_si_dump_for_actor(sim_info, sim, social_partners)
                except Exception:
                    pass
    except Exception:
        pass

    return SerializedSim(
        sim_id=sid,
        sim_id_str=str(sim_info.id),
        first_name=str(sim_info.first_name),
        last_name=str(sim_info.last_name),
        age=sim_info.age.name if sim_info.age is not None else None,
        gender=sim_info.gender.name if sim_info.gender is not None else None,
        is_npc=bool(sim_info.is_npc),
        household_id=(
            int(sim_info.household_id) if sim_info.household_id is not None else None
        ),
        zone_id=int(sim_info.zone_id) if sim_info.zone_id is not None else None,
        interactions_running=running,
        interactions_queue=queued,
        social_partner_sim_ids=social_partners,
    )
