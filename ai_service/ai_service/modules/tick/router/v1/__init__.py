from dataclasses import asdict

from fastapi import APIRouter

from ai_service.deps import TickStoreDep, ViewerHubDep
from ai_service.modules.tick.schemas import TickRequestSchema, TickResponseSchema

__all__ = ("router",)

router = APIRouter(prefix="/tick")


@router.post("", response_model=TickResponseSchema)
def post_tick(
    body: TickRequestSchema, store: TickStoreDep, hub: ViewerHubDep
) -> TickResponseSchema:
    response = TickResponseSchema(protocol_version="1.0", decisions=[])
    store.record_tick(body.model_dump(), response.model_dump())
    hub.publish_snapshot_threadsafe(asdict(store.get_snapshot()))
    return response
