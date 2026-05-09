# ai_service

FastAPI app implementing [`PROTOCOL.md`](../PROTOCOL.md) (`POST /v1/tick`).

## Setup

Install dependencies (run from this `ai_service/` directory):

```bash
uv sync
```

Generate `EA/` (shared with IDE support for both `npc_ai_mod` and this package; run from the **repository root**):

```bash
cp .env.example .env   # set GAME_DIR
./decompile_ea.sh
```

## Run

From this directory:

```bash
uv sync
uv run uvicorn ai_service.main:app --host 127.0.0.1 --port 8765
```

Smoke check:

```bash
curl -s http://127.0.0.1:8765/health
```

## EA types in the server

[`game_types.py`](game_types.py) shows how to reference decompiled Sims 4 modules under **`TYPE_CHECKING`** so Pyright can resolve `EA/` without importing EA code at runtime. Expand imports as your snapshot logic grows.
