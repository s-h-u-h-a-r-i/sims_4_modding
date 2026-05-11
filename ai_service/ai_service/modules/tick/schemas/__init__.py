"""
Pydantic schemas for the /v1/tick bridge endpoint.

Defines strict wire protocol types for HTTP serialization/deserialization. All models
reflect the current protocol version. Amend fields and descriptions in lockstep with PROTOCOL.md.
"""

from typing import Annotated, Any, Dict, List, Literal

from pydantic import BaseModel, Field

__all__ = (
    "DecisionItemSchema",
    "ModLogEntrySchema",
    "OutcomeSchema",
    "TickRequestSchema",
    "TickResponseSchema",
)


class DecisionItemSchema(BaseModel):
    """One AI decision returned in POST /v1/tick (flat shape consumed by npc_ai_mod)."""

    id: Annotated[
        str,
        Field(
            ...,
            description=(
                "Opaque id for this decision; the game mod sends it back as outcomes[].decision_id."
            ),
        ),
    ]
    sim_id: Annotated[
        int | str,
        Field(
            ...,
            description="Target Sim id (int from game snapshot; viewer may send string).",
        ),
    ]
    action: Annotated[
        str,
        Field(
            ...,
            description='Registered action in the mod (e.g. "go_home").',
        ),
    ]


class ModLogEntrySchema(BaseModel):
    timestamp_utc: Annotated[
        str,
        Field(..., description="UTC time when the log line was produced (ISO 8601)."),
    ]
    level: Annotated[
        Literal["debug", "info", "error"],
        Field(..., description="Severity for display and filtering in the viewer."),
    ]
    tag: Annotated[
        str,
        Field(default="", description="Short source label from the game mod."),
    ]
    message: Annotated[
        str,
        Field(default="", description="Human-readable detail."),
    ]
    traceback: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional stack trace or exception repr for errors.",
        ),
    ]


class TickInfoSchema(BaseModel):
    """Metadata information for a simulation tick."""

    id: Annotated[
        int,
        Field(
            default=0,
            description=(
                "Monotonically increasing integer ID for the current tick. "
                "Defaults to 0 if unset."
            ),
        ),
    ]
    timestamp_utc: Annotated[
        str,
        Field(
            ...,
            description=(
                "UTC timestamp (ISO8601 format) "
                "representing the wall clock time of this tick."
            ),
        ),
    ]


class WorldSnapshotSchema(BaseModel):
    """Snapshot of the relevant world state for this tick."""

    lot_id: Annotated[
        int | None,
        Field(
            default=None,
            description=(
                "Unique identifier of the lot (location) being simulated. "
                "Null if not applicable."
            ),
        ),
    ]
    zone_id: Annotated[
        int | None,
        Field(
            default=None,
            description="Unique identifier of the current zone. Null if not applicable.",
        ),
    ]
    sims: Annotated[
        List[Dict[str, Any]],
        Field(
            default_factory=list,
            description=(
                "List of dictionaries representing the current state of each Sim. "
                "Each dictionary should conform to the SimInfo wire schema."
            ),
        ),
    ]


class OutcomeSchema(BaseModel):
    """Outcome reported by the mod for a previously dispatched decision."""

    decision_id: Annotated[
        str,
        Field(..., description="The id of the decision returned in the previous tick response."),
    ]
    status: Annotated[
        Literal["success", "failure"],
        Field(..., description="Whether the decision was applied successfully in the game."),
    ]
    reason: Annotated[
        str | None,
        Field(
            default=None,
            description="Human-readable reason, populated on failure or for additional context.",
        ),
    ]


class TickRequestSchema(BaseModel):
    """Payload structure for a /v1/tick POST request."""

    tick: Annotated[
        TickInfoSchema,
        Field(..., description="Metadata for this tick. See TickInfoSchema."),
    ]
    world: Annotated[
        WorldSnapshotSchema,
        Field(..., description="World state snapshot relevant to this tick."),
    ]
    outcomes: Annotated[
        List[OutcomeSchema],
        Field(
            default_factory=list,
            description=(
                "Outcomes for decisions dispatched in the previous tick response. "
                "Empty on the first tick or when no decisions were sent."
            ),
        ),
    ]
    logs: Annotated[
        List[ModLogEntrySchema],
        Field(
            default_factory=list,
            description=(
                "Buffered log lines from the game mod; forwarded to the viewer over WebSocket."
            ),
        ),
    ]


class TickResponseSchema(BaseModel):
    """Response schema for decisions produced during this tick."""

    protocol_version: Annotated[
        str,
        Field(
            default="1.0",
            description=(
                "Protocol version for compatibility checks. "
                "Always '1.0' for this schema version."
            ),
        ),
    ]
    decisions: Annotated[
        List[DecisionItemSchema],
        Field(
            default_factory=list,
            description="Commands to run in-game before the next tick (id, sim_id, action).",
        ),
    ]
