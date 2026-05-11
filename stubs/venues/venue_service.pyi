from typing import Optional, Tuple

from sims.sim_info import SimInfo

class Venue:
    def summon_npcs(
        self,
        npc_infos: Tuple[SimInfo, ...],
        purpose: int,
        host_sim_info: Optional[SimInfo] = None,
    ) -> None: ...

class VenueService:
    active_venue: Venue

    def on_loading_screen_animation_finished(self, *args: object, **kwargs: object) -> None: ...
