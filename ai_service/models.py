"""Request/response models for POST /v1/tick (see PROTOCOL.md)."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class TickInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[
        int | None,
        Field(default=None, description="Monotonic tick from the mod (optional in v1)"),
    ]
    timestamp_utc: Annotated[
        str, Field(description="ISO 8601 timestamp when snapshot was taken")
    ]


class SimSnapshot(BaseModel):
    """One Sim in the snapshot; extend as sim_state.py grows."""

    model_config = ConfigDict(extra="allow")

    sim_id: int
    first_name: str | None = None
    last_name: str | None = None
    is_npc: bool | None = None


class WorldState(BaseModel):
    """Extensible world envelope."""

    model_config = ConfigDict(extra="allow")

    lot_id: int | None = None
    zone_id: int | None = None
    sims: list[SimSnapshot] = Field(default_factory=list)


class TickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick: TickInfo
    world: WorldState


class ActionPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Decision kind, e.g. push_interaction")
    interaction_guid: str | None = None
    reason: str | None = None


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_sim_id: int
    action: ActionPayload


class TickResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str = "1.0"
    decisions: list[Decision] = Field(default_factory=list)


# Loose JSON used when you deliberately bypass strict models (advanced helpers).
EAJson = dict[str, Any]
