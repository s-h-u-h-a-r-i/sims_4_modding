"""
Pydantic schemas for the /v1/tick bridge endpoint.

Defines strict wire protocol types for HTTP serialization/deserialization. All models
reflect the current protocol version. Amend fields and descriptions in lockstep with PROTOCOL.md.
"""

from typing import Annotated, Any, Dict, List

from pydantic import BaseModel, Field

__all__ = ("TickRequestSchema", "TickResponseSchema")


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
        List[Dict[str, Any]],
        Field(
            default_factory=list,
            description=(
                "List of dictionaries representing individual AI "
                "decisions/actions in response to the tick."
            ),
        ),
    ]
