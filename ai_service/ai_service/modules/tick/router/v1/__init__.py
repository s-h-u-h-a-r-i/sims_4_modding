from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ai_service.deps import TickStoreWsDep, ViewerHubWsDep
from ai_service.modules.tick.router.v1.handlers import tick_response_from_request
from ai_service.modules.tick.schemas import TickRequestSchema

__all__ = ("router",)

router = APIRouter(prefix="/tick")


@router.websocket("")
async def websocket_tick(
    websocket: WebSocket,
    store: TickStoreWsDep,
    hub: ViewerHubWsDep,
) -> None:
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                body = TickRequestSchema.model_validate_json(raw)
            except ValidationError:
                await websocket.close(code=1007)
                return
            resp = tick_response_from_request(body, store, hub)
            await websocket.send_text(resp.model_dump_json())
    except WebSocketDisconnect:
        pass
