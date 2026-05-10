from dataclasses import asdict
from typing import Any, Dict

from fastapi import APIRouter, Request

from ai_service.deps import TickStoreDep, ViewerHubDep
from ai_service.modules.tick.schemas import TickRequestSchema, TickResponseSchema

__all__ = ("router",)

router = APIRouter(prefix="/tick")


@router.post("", response_model=TickResponseSchema)
async def post_tick(
    request: Request,
    store: TickStoreDep,
    hub: ViewerHubDep,
) -> TickResponseSchema:
    raw: Dict[str, Any] = await request.json()
    body = TickRequestSchema.model_validate(raw)
    decisions = store.pop_commands()
    response = TickResponseSchema(protocol_version="1.0", decisions=decisions)
    store.record_tick(body.model_dump(), response.model_dump())
    hub.publish_snapshot_threadsafe(asdict(store.get_snapshot()))
    return response
