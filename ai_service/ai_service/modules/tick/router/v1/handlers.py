"""Shared WebSocket tick request handling."""

from dataclasses import asdict

from ai_service.modules.tick.schemas import TickRequestSchema, TickResponseSchema
from ai_service.modules.tick.services import TickStore
from ai_service.modules.viewer.services import ViewerBroadcastHub


def tick_response_from_request(
    body: TickRequestSchema,
    store: TickStore,
    hub: ViewerBroadcastHub,
) -> TickResponseSchema:
    store.ensure_bridge_session(body.tick.bridge_session_id)
    if body.outcomes:
        store.record_outcomes(body.outcomes)
    decisions = store.pop_commands()
    response = TickResponseSchema(protocol_version="1.0", decisions=decisions)
    log_payload = [e.model_dump() for e in body.logs]
    store.note_tick_received()
    hub.publish_tick_frame_threadsafe(body.tick.model_dump(), body.world.model_dump())
    hub.publish_snapshot_threadsafe(asdict(store.get_snapshot()))
    if log_payload:
        hub.publish_mod_logs_threadsafe(log_payload)
    return response
