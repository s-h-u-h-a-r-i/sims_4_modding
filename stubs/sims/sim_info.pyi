from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple, Type

from sims.sim_info_types import Age, Gender
if TYPE_CHECKING:
    from sims.sim import Sim


class SimInfo:
    # ── Identity ──────────────────────────────────────────────────────────────
    id: int
    sim_id: int  # alias for id
    first_name: str
    last_name: str
    age: Age
    gender: Gender
    species: int  # 1=human, 2=dog, 3=cat, 5=fox, 6=horse
    household_id: int
    sim_template_id: int

    # ── Boolean age helpers ───────────────────────────────────────────────────
    is_baby: bool
    is_infant: bool
    is_toddler: bool
    is_child: bool
    is_teen: bool
    is_young_adult: bool
    is_adult: bool
    is_elder: bool
    is_child_or_older: bool
    is_teen_or_older: bool
    is_teen_or_younger: bool

    # ── Boolean state ─────────────────────────────────────────────────────────
    is_npc: bool
    is_selectable: bool
    is_selected: bool
    is_player_sim: bool
    is_played_sim: bool
    is_human: bool
    is_pet: bool
    is_male: bool
    is_female: bool
    is_ghost: bool
    is_dead: bool
    is_pregnant: bool
    is_at_home: bool
    is_mobile: bool
    is_simulating: bool
    is_premade_sim: bool
    lives_here: bool
    can_live_alone: bool
    can_instantiate_sim: bool
    has_custom_career: bool

    # ── Aging ─────────────────────────────────────────────────────────────────
    age_progress: float
    age_progress_percentage: float
    time_until_age_up: float
    auto_aging_enabled: bool

    # ── Relationships / family ────────────────────────────────────────────────
    spouse_sim_id: Optional[int]
    fiance_sim_id: Optional[int]

    # ── Zone / world ──────────────────────────────────────────────────────────
    zone_id: int
    world_id: int
    vacation_or_home_zone_id: int
    roommate_zone_id: int

    # ── Traits ────────────────────────────────────────────────────────────────
    trait_ids: List[int]

    # ── Careers ───────────────────────────────────────────────────────────────
    careers: dict  # {career_uid: Career}

    # ── Occult ────────────────────────────────────────────────────────────────
    current_occult_types: object  # OccultType enum flag
    occult_types: object          # OccultType enum flag

    # ── Physical ──────────────────────────────────────────────────────────────
    skin_tone: int
    skin_tone_val_shift: float
    fat: float   # -40..40; negative = thin, positive = fat
    fit: float   # -40..40; positive = muscular

    # ── Other readable values ─────────────────────────────────────────────────
    death_type: object          # DeathType enum
    pregnancy_progress: float   # 0.0 – 1.0
    satisfaction_tracker: Optional[object]
    is_exploring_sexuality: bool
    voice_pitch: float          # 0.0 – 1.0
    lod: object                 # SimInfoLODLevel enum

    # ── Trackers (call methods on these) ─────────────────────────────────────
    career_tracker: object
    trait_tracker: object
    relationship_tracker: object
    commodity_tracker: object
    statistic_tracker: object
    aspiration_tracker: Optional[object]
    death_tracker: object
    pregnancy_tracker: object
    genealogy: object
    degree_tracker: object

    # ── Class-level tuning constants ─────────────────────────────────────────
    SIM_SKEWER_AFFORDANCES: Tuple[Type[Any], ...]
    DEFAULT_AWAY_ACTION: Dict[Type[Any], Any]  # keys are motive commodity classes

    # ── Methods ───────────────────────────────────────────────────────────────
    def get_sim_instance(self) -> "Optional[Sim]": ...

    # Traits
    def has_trait(self, trait: object) -> bool: ...
    def has_any_trait(self, traits: object) -> bool: ...
    def get_traits(self) -> Iterator[object]: ...
    def add_trait(self, trait: object) -> bool: ...
    def remove_trait(self, trait: object) -> bool: ...

    # Mood / buffs
    def get_mood(self) -> object: ...
    def get_mood_intensity(self) -> int: ...
    def has_buff(self, buff_type: object) -> bool: ...
    def add_buff(self, buff_type: object, **kwargs: object) -> object: ...
    def remove_buff_by_type(self, buff_type: object) -> None: ...

    # Statistics / needs
    def get_stat_value(self, stat_type: object) -> float: ...
    def get_stat_instance(self, stat_type: object, add: bool = ...) -> Optional[object]: ...
    def set_stat_value(self, stat_type: object, value: float) -> None: ...
    def get_statistic(self, stat_type: object, add: bool = ...) -> Optional[object]: ...

    # Satisfaction
    def get_satisfaction_points(self) -> int: ...

    # Outfit
    def get_current_outfit(self) -> Tuple[object, int]: ...
    def set_current_outfit(self, outfit: Tuple[object, int]) -> None: ...

    # Aging
    def advance_age(self) -> None: ...
    def can_age_up(self) -> bool: ...

    # Situations / zone
    def get_current_situations_gen(self) -> Iterator[object]: ...
    def is_in_travel_group(self) -> bool: ...
    def is_instanced(self, allow_hidden_flags: object = ...) -> bool: ...

    # Family / relations
    def get_spouse_sim_info(self) -> Optional["SimInfo"]: ...
    def get_significant_other_sim_info(self) -> Optional["SimInfo"]: ...
    def get_family_sim_ids_gen(self) -> Iterator[int]: ...

    # Misc
    def get_attracted_genders(self) -> object: ...
    def log_sim_info(self) -> None: ...
    def is_busy(self) -> bool: ...
    def can_go_to_work(self) -> bool: ...
    def all_skills(self) -> List[object]: ...
    def top_skills(self, count: int = ...) -> List[object]: ...
