"""API router: /v1/*"""

from fastapi import APIRouter

from ai_service.models import TickRequest, TickResponse

router = APIRouter(prefix="/v1", tags=["v1"])


@router.post("/tick", response_model=TickResponse)
def post_tick(payload: TickRequest) -> TickResponse:
    """
    Receive a snapshot from the game; return decisions for director.py.

    Replace the body with model/LLM calls; keep TickRequest/TickResponse in sync with PROTOCOL.md.
    """
    _ = payload  # placeholder until policy/LLM is wired
    return TickResponse(
        protocol_version="1.0",
        decisions=[],
    )
