# NPC AI Bridge — HTTP protocol

Defines how **`npc_ai_mod`** (game, Python 3.7, stdlib `http.client`) talks to **`ai_service`** (local or hosted, recommended stack: FastAPI).

- **Wire format:** JSON over HTTP/HTTPS.
- **Direction:** Game is always the **client**; server never calls into the player’s PC (no inbound webhooks from the hosted API).

## Versioning

- Path prefix **`/v1/`** — bump to `/v2/` when you make incompatible request/response changes.
- Optional response field **`protocol_version`** (string, e.g. `"1.0"`) lets the server signal support without breaking older mods.

## Base URL

| Environment | Example base URL |
|-------------|-------------------|
| Local dev   | `http://127.0.0.1:8765` |
| Hosted      | `https://api.example.com` |

The game mod should read base URL from a player-editable config (see repo docs when implemented). Default for development: `http://127.0.0.1:8765`.

## Authentication (optional)

For local dev, auth is usually omitted.

For hosted deployments, use a header:

```http
Authorization: Bearer <token>
```

Token source is out of scope for the wire spec; store it in the same mod config as the base URL.

## Primary endpoint: tick (single round-trip)

**`POST /v1/tick`**

One request carries the current world snapshot; the response carries all decisions to apply before the next tick. This matches the game’s constraints (simple client, no WebSocket required).

### Request

- **Headers:** `Content-Type: application/json`
- **Body:** JSON object. Minimum shape:

```json
{
  "tick": {
    "id": 0,
    "timestamp_utc": "2026-05-09T17:00:00Z"
  },
  "world": {
    "lot_id": null,
    "zone_id": null,
    "sims": []
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tick.id` | integer | Monotonic tick counter from the mod (optional for v1). |
| `tick.timestamp_utc` | string (ISO 8601) | When the snapshot was taken. |
| `world` | object | Extensible; add fields as `sim_state.py` grows. |
| `world.sims` | array | One entry per NPC (or all controllable actors — policy is mod-side). |

**Per-sim entry (illustrative, extend freely):**

```json
{
  "sim_id": 12345,
  "first_name": "Jordan",
  "last_name": "Kim",
  "is_npc": true,
  "notes": "mod-defined fields only; no need to mirror full EA objects"
}
```

### Response

- **Status:** `200 OK` for success.
- **Body:** JSON object:

```json
{
  "protocol_version": "1.0",
  "decisions": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `protocol_version` | string | Optional; server capability hint. |
| `decisions` | array | Actions for `director.py` to apply (see below). |

**Decision item (illustrative):**

```json
{
  "target_sim_id": 12345,
  "action": {
    "type": "push_interaction",
    "interaction_guid": "0xDEADBEEF",
    "reason": "optional human/LLM debug string"
  }
}
```

`action.type` is an open set; document new types in this file as you add them. Unknown types should be ignored by the mod with a log line.

### Errors

| Status | Meaning |
|--------|---------|
| `400` | Malformed JSON or validation error (FastAPI/Pydantic detail in body). |
| `401` / `403` | Auth failed (when using hosted + bearer token). |
| `422` | Semantically invalid payload (Pydantic). |
| `500` | Server/model failure — mod should log and skip applying decisions. |

Response body on errors may be JSON (`{"detail": ...}` in FastAPI) or plain text; the mod should not depend on a specific error schema.

## Optional: two-step API (not required for v1)

If you prefer split IO for debugging:

| Method | Path | Role |
|--------|------|------|
| `POST` | `/v1/state` | Push snapshot only; `204` or `200` with `{ "accepted": true }`. |
| `GET` | `/v1/decisions` | Poll decisions (query params TBD). |

The in-game client is simpler with **`POST /v1/tick` only**; implement these only if you need them.

## Client behaviour (mod)

- **Timeout:** Every request should use a bounded timeout (e.g. 5–15 seconds) so a hung model does not freeze gameplay.
- **Retries:** Optional, conservative (e.g. one retry on connection errors). Avoid unbounded loops.
- **HTTPS:** Use default certificate verification for hosted URLs; document any dev-only exceptions.

## Server implementation notes (FastAPI)

- Expose **`POST /v1/tick`** with a Pydantic model for request/response so the schema stays documented in code.
- Run with **uvicorn** locally, e.g. `uvicorn main:app --host 127.0.0.1 --port 8765`.
- **CORS:** Not required for the Sims 4 mod (it is not a browser). Enable CORS only if you add a browser-based debug UI.

## Changelog

| Version | Change |
|---------|--------|
| 1.0 (draft) | Initial `POST /v1/tick` contract. |
