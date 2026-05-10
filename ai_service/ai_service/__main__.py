"""
FastAPI entrypoint.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ai_service import __version__
from ai_service.modules.tick.router import tick_v1_router
from ai_service.modules.tick.services import TickStore
from ai_service.modules.viewer.router import STATIC_DIR, viewer_v1_router
from ai_service.modules.viewer.services import ViewerBroadcastHub


@asynccontextmanager
async def lifespan(_app: FastAPI):
    app.state.tick_store = TickStore()
    app.state.viewer_hub = ViewerBroadcastHub()

    loop = asyncio.get_running_loop()
    app.state.viewer_hub.bind_event_loop(loop)
    consumer = asyncio.create_task(app.state.viewer_hub.run_broadcast_consumer())

    try:
        yield
    finally:
        consumer.cancel()
        try:
            await consumer
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="npc ai bridge",
    version=__version__,
    description="HTTP bridge between npc_ai_mod and your AI/policy layer. See PROTOCOL.md.",
    lifespan=lifespan,
)

app.include_router(tick_v1_router, prefix="/v1", tags=["tick-v1"])
app.include_router(viewer_v1_router, prefix="/v1", tags=["viewer-v1"])

app.mount(
    "/v1/viewer/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="viewer-static",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "npc_ai.bridge"}
