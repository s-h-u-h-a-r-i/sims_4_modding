from typing import Annotated

from fastapi import Depends, Request, WebSocket

from ai_service.modules.tick.services import TickStore
from ai_service.modules.viewer.services import ViewerBroadcastHub

__all__ = ("TickStoreDep", "ViewerHubDep", "ViewerHubWsDep")


def get_tick_store(request: Request) -> TickStore:
    return request.app.state.tick_store


def get_viewer_hub(request: Request) -> ViewerBroadcastHub:
    return request.app.state.viewer_hub


def get_viewer_hub_ws(websocket: WebSocket) -> ViewerBroadcastHub:
    return websocket.app.state.viewer_hub


TickStoreDep = Annotated[TickStore, Depends(get_tick_store)]
ViewerHubDep = Annotated[ViewerBroadcastHub, Depends(get_viewer_hub)]
ViewerHubWsDep = Annotated[ViewerBroadcastHub, Depends(get_viewer_hub_ws)]
