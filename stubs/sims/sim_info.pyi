from typing import Optional
from sims.sim_info_types import Age, Gender

class SimInfo:
    id: int
    first_name: str
    last_name: str
    age: Age
    gender: Gender
    is_npc: bool
    household_id: Optional[int]

    def get_sim_instance(self) -> Optional[object]: ...
