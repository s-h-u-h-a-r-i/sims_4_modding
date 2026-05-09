from fastapi import APIRouter

from ai_service.modules.tick.schemas import TickRequestSchema, TickResponseSchema

__all__ = ("router",)

router = APIRouter(prefix="/tick")


@router.post("", response_model=TickResponseSchema)
def post_tick(_body: TickRequestSchema) -> TickResponseSchema:
    return TickResponseSchema(protocol_version="1.0", decisions=[])
