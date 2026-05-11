from dataclasses import asdict

from fastapi import APIRouter

from ai_service.deps import TickStoreDep, ViewerHubDep
from ai_service.modules.tick.schemas import TickRequestSchema, TickResponseSchema

__all__ = ("router",)

router = APIRouter(prefix="/tick")


@router.post("", response_model=TickResponseSchema)
async def post_tick(
    body: TickRequestSchema,
    store: TickStoreDep,
    hub: ViewerHubDep,
) -> TickResponseSchema:
    if body.outcomes:
        store.record_outcomes([o.model_dump() for o in body.outcomes])
    decisions = store.pop_commands()
    response = TickResponseSchema(protocol_version="1.0", decisions=decisions)
    log_payload = [e.model_dump() for e in body.logs]
    store.note_tick_received()
    hub.publish_tick_frame_threadsafe(
        body.tick.model_dump(),
        body.world.model_dump(),
    )
    hub.publish_snapshot_threadsafe(asdict(store.get_snapshot()))
    if log_payload:
        hub.publish_mod_logs_threadsafe(log_payload)
    return response
