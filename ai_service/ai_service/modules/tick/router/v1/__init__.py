from fastapi import APIRouter

from ai_service.modules.tick.schemas import TickRequestSchema, TickResponseSchema
from ai_service.modules.tick.services import TickStore

__all__ = ("router",)

router = APIRouter(prefix="/tick")


@router.post("", response_model=TickResponseSchema)
def post_tick(body: TickRequestSchema) -> TickResponseSchema:
    store = TickStore()
    response = TickResponseSchema(protocol_version="1.0", decisions=[])
    store.record_tick(body.model_dump(), response.model_dump())
    return response
