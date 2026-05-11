from __future__ import annotations

import typing

import services
from sims.sim_info import SimInfo
from venues.venue_constants import NPCSummoningPurpose

from ...logutil import log_error, log_info

__all__ = ("apply_summon_sim",)


def apply_summon_sim(sim_info: SimInfo) -> typing.Tuple[bool, typing.Optional[str]]:
    """Summon an off-lot Sim through venue NPC summoning (visit / invite-style)."""
    try:
        if sim_info.get_sim_instance() is not None:
            log_info(
                "actions.apply_summon_sim",
                f"{sim_info.first_name} {sim_info.last_name} already instanced, noop",
            )
            return True, None

        zone = services.current_zone()
        if zone is None:
            msg = "no current zone"
            log_info("actions.apply_summon_sim", msg)
            return False, msg

        venue_service = zone.venue_service
        if venue_service is None:
            msg = "no venue service"
            log_info("actions.apply_summon_sim", msg)
            return False, msg

        active_venue = venue_service.active_venue
        if active_venue is None:
            msg = "no active venue"
            log_info("actions.apply_summon_sim", msg)
            return False, msg

        host = services.active_sim_info()
        if sim_info.is_npc:
            active_venue.summon_npcs(
                (sim_info,),
                NPCSummoningPurpose.DEFAULT,
                host,
            )
            purpose_name = "DEFAULT"
        else:
            active_venue.summon_npcs(
                (sim_info,),
                NPCSummoningPurpose.BRING_PLAYER_SIM_TO_LOT,
            )
            purpose_name = "BRING_PLAYER_SIM_TO_LOT"

        log_info(
            "actions.apply_summon_sim",
            f"summon_npcs {purpose_name} sim_id={sim_info.sim_id} "
            f"({sim_info.first_name} {sim_info.last_name}) "
            f"host_sim_id={int(host.sim_id) if host is not None else None}",
        )
        return True, None
    except Exception as exc:
        log_error("actions.apply_summon_sim", "summon_npcs failed", exc)
        return False, str(exc)
