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
- **Body:** JSON object. Shape implemented today by `npc_ai_mod` / `ai_service`:

```json
{
  "tick": {
    "id": 0,
    "timestamp_utc": "2026-05-09T17:00:00Z",
    "bridge_session_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "world": {
    "lot_id": null,
    "zone_id": null,
    "sims": []
  },
  "outcomes": [],
  "logs": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tick.id` | integer | Monotonic tick counter from the mod (starts at 1 on first POST in a zone session). |
| `tick.timestamp_utc` | string (ISO 8601) | When the snapshot was taken. |
| `tick.bridge_session_id` | string (UUID) | New value each game/script reload; `ai_service` clears viewer/command history when this changes (optional field for backwards compatibility when omitted). |
| `world` | object | Zone/lot context plus instanced Sims (`npc_ai_mod.sim_state.get_world_state()`). |
| `world.lot_id` | integer \| null | Active lot id when available. |
| `world.zone_id` | integer \| null | Current zone id when available. |
| `world.sims` | array | One object per **instanced** Sim in the zone (see below). |
| `outcomes` | array | Optional. Outcomes for decisions **dispatched in the previous** tick response (see below). On the wire the mod **omits** this key when there are none (first tick, or no prior decisions). |
| `logs` | array | Optional. Buffered mod log lines for the viewer (`logutil`); levels `debug`, `info`, `error`. Omitted when nothing is drained. **Max entries per drain** depends on baked mod profile (`npc_ai_mod/npc_ai_mod/config/profiles/` → `generated.py`, e.g. production 250 vs development thousands when SI dumps are enabled). |

**Per-sim entry** (`SerializedSim` / `sim_state.serialize_sim` in the `sim_state` package):

| Field | Type | Description |
|-------|------|-------------|
| `sim_id` | integer | Game Sim id. |
| `sim_id_str` | string | Same id as string (stable for JSON / JS). |
| `first_name`, `last_name` | string | |
| `age` | string \| null | EA age enum name, e.g. `ADULT`. |
| `gender` | string \| null | EA gender enum name. |
| `is_npc` | boolean | |
| `household_id` | integer \| null | |
| `zone_id` | integer \| null | Sim’s zone id when set. |
| `interactions_running` | array | `{ "interaction_id", "interaction_id_str", "class_name" }` per running super interaction. |
| `interactions_queue` | array | Same fields plus `is_queue_head` (boolean). |
| `social_partner_sim_ids` | array[string] | Other Sim ids (**stringified**) that share SI social-thread linkage or inferred **shared-prop** cohort (same snapshot); safe for JS `BigInt` round-trip via `sim_id_str`. |

**Outcome item** (matches `OutcomeSchema` / `DecisionOutcome`):

```json
{
  "decision_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "reason": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `decision_id` | string | Must match the `id` field from the corresponding decision in the prior response. |
| `status` | string | `success` or `failure`. |
| `reason` | string \| null | Human-readable detail (especially on failure). |

**Log item** (matches `ModLogEntrySchema` / `LogEntry`):

| Field | Type | Description |
|-------|------|-------------|
| `timestamp_utc` | string | ISO 8601. |
| `level` | string | `debug`, `info`, or `error`. |
| `tag` | string | Source label. |
| `message` | string | Log text. |
| `traceback` | string \| null | Optional; error stack / repr. |

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
| `protocol_version` | string | Optional; server capability hint (`ai_service` sends `1.0`). |
| `decisions` | array | Flat commands for `actions.apply_decisions()` (see below). |

**Decision item** — flat object (matches `ServerDecision`; parsed by `schemas.parse_tick_response`):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "sim_id": 12345,
  "action": "go_home"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable id for this decision; the mod echoes it in the next request’s `outcomes[].decision_id`. |
| `sim_id` | integer or string | Target Sim id (`ai_service` / viewer may use string; the mod resolves it with `int(str(sim_id))`). |
| `action` | string | Registered handler name in the mod (see table below). |

The `ai_service` viewer queues WebSocket commands as dictionaries that may include extra keys (e.g. `type: "command"`); the mod only reads `id`, `sim_id`, and `action`.

**Supported actions** (extend in `npc_ai_mod/actions.py` and document here):

| `action` | Behaviour |
|----------|-----------|
| `go_home` | Push go-home affordance (`SIM_SKEWER_AFFORDANCES[0]`) at high priority. |

Unknown `action` values produce a **failure** outcome with reason `unknown action ...`; the server may still record that in viewer history.

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
| 1.0 | Documented real request fields (`outcomes`, `logs`), full `SerializedSim` shape, flat `decisions` (`id` / `sim_id` / `action`), and **`tick.bridge_session_id`** so hosted/viewer state can reset when Sims 4 reloads the mod scripts. |
