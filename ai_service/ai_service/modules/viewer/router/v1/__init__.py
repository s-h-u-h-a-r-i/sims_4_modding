from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from ai_service.modules.tick.services import TickStore

__all__ = ("router",)

_VIEWER_HTML = Path(__file__).resolve().parents[4] / "static" / "viewer.html"

router = APIRouter(prefix="/viewer")


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
def viewer_state_json() -> JSONResponse:
    store = TickStore()
    snapshot = asdict(store.get_snapshot())
    return JSONResponse(content=snapshot)
