# ai_service

FastAPI app implementing [`PROTOCOL.md`](../PROTOCOL.md): **`WebSocket /v1/tick`** from the game mod plus the viewer APIs.

## Setup

Install dependencies (run from this `ai_service/` directory):

```bash
uv sync
```

Generate `EA/` (shared with IDE support for both `npc_ai_mod` and this package; run from the **repository root**). Set `GAME_DIR` in **`npc_ai_mod/.env`** (copy from `npc_ai_mod/.env.example`), then:

```bash
./decompile_ea.sh
```

## Run

From this directory:

```bash
uv sync
uv run python -m ai_service.__main__
```

``python -m ai_service.__main__`` starts Uvicorn with **WebSocket auto-ping disabled** (the mod only reads ``/v1/tick`` during each exchange; default Uvicorn pings yield *keepalive ping timeout*, 1011). Host, port, and reload come from **Pydantic Settings**: env ``NPC_AI_BRIDGE_*`` and optional ``ai_service/.env`` (see [``.env.example``](.env.example)). If you start plain ``uvicorn`` elsewhere, pass ``ws_ping_interval=None`` and ``ws_ping_timeout=None`` or you will break the game client.

Smoke check:

```bash
curl -s http://127.0.0.1:8765/health
```

## EA types in the server

[`game_types.py`](game_types.py) shows how to reference decompiled Sims 4 modules under **`TYPE_CHECKING`** so Pyright can resolve `EA/` without importing EA code at runtime. Expand imports as your snapshot logic grows.
