import asyncio
import json
from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from ai_service.core.constants import STATIC_DIR
from ai_service.deps import TickStoreDep, TickStoreWsDep, ViewerHubWsDep

__all__ = ("router",)

_VIEWER_HTML = STATIC_DIR / "viewer.html"

router = APIRouter(prefix="/viewer")


@router.websocket("/ws")
async def viewer_ws(
    websocket: WebSocket, store: TickStoreWsDep, hub: ViewerHubWsDep
) -> None:
    await hub.register(websocket)
    try:
        await websocket.send_json(asdict(store.get_snapshot()))
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                msg = json.loads(raw)
                msg_type = msg.get("type")

                if msg_type == "command":
                    store.push_command(msg)

                elif msg_type == "set_ai_enabled":
                    store.set_ai_enabled(bool(msg.get("enabled", True)))
                    # Immediately reflect change in all connected viewers
                    await hub.broadcast_json(asdict(store.get_snapshot()))

            except asyncio.TimeoutError:
                continue
            except (json.JSONDecodeError, AttributeError):
                pass
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unregister(websocket)


@router.get("", response_class=HTMLResponse, response_model=None)
def viewer_page() -> HTMLResponse:
    if _VIEWER_HTML.is_file():
        return HTMLResponse(
            content=_VIEWER_HTML.read_text(encoding="utf-8"),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": "inline"},
        )
    return HTMLResponse(
        content=(
            f"<!doctype html><meta charset=utf-8><title>npc ai viewer</title>"
            f"<p>missing static/viewer.html in package</p>"
            f"<p>Was looking for: <code>{_VIEWER_HTML!s}</code></p>"
        ),
        status_code=500,
    )


@router.get("/state.json", response_class=JSONResponse)
def viewer_state_json(store: TickStoreDep) -> JSONResponse:
    snapshot = asdict(store.get_snapshot())
    return JSONResponse(content=snapshot)
