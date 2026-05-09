"""
FastAPI entrypoint.
"""

from fastapi import FastAPI

from ai_service import __version__
from ai_service.modules.tick.router import tick_v1_router

app = FastAPI(
    title="npc ai bridge",
    version=__version__,
    description="HTTP bridge between npc_ai_mod and your AI/policy layer. See PROTOCOL.md.",
)

app.include_router(tick_v1_router, prefix="/v1", tags=["tick-v1"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "npc_ai.bridge"}
