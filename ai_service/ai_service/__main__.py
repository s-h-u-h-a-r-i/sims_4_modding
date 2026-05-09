"""
FastAPI entrypoint.

Run from this directory (after `uv sync`):

  uv run uvicorn ai_service.main:app --host 127.0.0.1 --port 8765
"""

from fastapi import FastAPI

from ai_service import __version__
from ai_service.router_v1 import router as v1_router

app = FastAPI(
    title="npc_ai bridge",
    version=__version__,
    description="HTTP bridge between npc_ai_mod and your AI/policy layer. See PROTOCOL.md.",
)

app.include_router(v1_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "npc_ai.bridge"}
