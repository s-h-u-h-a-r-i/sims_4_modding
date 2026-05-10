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
    store.record_tick(body.model_dump(), response.model_dump())
    hub.publish_snapshot_threadsafe(asdict(store.get_snapshot()))
    return response
