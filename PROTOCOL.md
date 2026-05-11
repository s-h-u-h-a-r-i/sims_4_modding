# NPC AI Bridge — WebSocket protocol

Defines how **`npc_ai_mod`** (game, Python 3.7, RFC **6455** WebSocket client built on the standard library `socket`) talks to **`ai_service`** (local or hosted; FastAPI is the reference implementation).

- **Wire format:** JSON payloads sent as WebSocket **text** frames (`UTF-8`).
- **Direction:** Game is always the **client**; nothing calls inbound into the player’s machine except the outbound connection they open.

## Versioning

- Path prefix **`/v1/`** — bump paths when message shapes stop being compatible (e.g. `/v2/tick`).
- Optional response field **`protocol_version`** (string, e.g. `"1.0"`) identifies the payload schema generation.

## Base URL

| Environment | Tick URL |
|-------------|----------|
| Local dev   | `ws://127.0.0.1:8765/v1/tick` |
| Hosted TLS  | `wss://api.example.com/v1/tick` |

Until config is surfaced in the mod, development expects **`127.0.0.1:8765`**.

## Primary endpoint — tick (`/v1/tick`)

The mod opens **one persistent WebSocket** to this path while the zone is loaded. Each simulation step that needs a bridge round-trip:

1. Client sends **one text frame** whose payload is **one JSON object** (below).
2. Server replies **one text frame** whose payload is **one JSON object** (response below).

Malformed JSON or a failed Pydantic parse: the server SHOULD close the connection with code **1007**; the mod SHOULD drop its socket and open a fresh connection on the next tick.

### Request JSON

Shape implemented by `npc_ai_mod` / `ai_service`:

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
| `tick.id` | integer | Monotonic tick counter from the mod (starts at 1 on the first outbound message in a zone session). |
| `tick.timestamp_utc` | string (ISO 8601) | When the snapshot was taken. |
| `tick.bridge_session_id` | string (UUID) | New value each game/script reload; `ai_service` resets viewer/command state keyed on the session when this value changes. |
| `world` | object | Zone/lot context plus instanced Sims (`npc_ai_mod.sim_state.get_world_state()`). |
| `world.lot_id` | integer \| null | Active lot id when available. |
| `world.zone_id` | integer \| null | Current zone id when available. |
| `world.sims` | array | One object per **instanced** Sim in the zone (see below). |
| `outcomes` | array | Outcomes for decisions **applied from the prior** tick response (see below). Omitted when there are none (`tick_payload_to_wire`). |
| `logs` | array | Buffered mod log lines for the viewer (`logutil`); levels `debug`, `info`, `error`. Omitted when nothing is drained. **Max entries per drain** follows the baked mod profile (`config/profiles/` → `generated.py`). |

**Per-sim entry** (`SerializedSim` via `sim_state.serialize_sim`):

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
| `social_partner_sim_ids` | array[string] | Other Sim ids (**stringified**) in SI social linkage or inferred **shared-prop** cohort; safe for JS `BigInt` via `sim_id_str`. |

**Outcome item** (`OutcomeSchema` / `DecisionOutcome`):

```json
{
  "decision_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "reason": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `decision_id` | string | Matches the `id` field from the decision in the prior response. |
| `status` | string | `success` or `failure`. |
| `reason` | string \| null | Human-readable detail (especially on failure). |

**Log item** (`ModLogEntrySchema` / `LogEntry`):

| Field | Type | Description |
|-------|------|-------------|
| `timestamp_utc` | string | ISO 8601. |
| `level` | string | `debug`, `info`, or `error`. |
| `tag` | string | Source label. |
| `message` | string | Log text. |
| `traceback` | string \| null | Optional stack / repr. |

### Response JSON

One JSON object:

```json
{
  "protocol_version": "1.0",
  "decisions": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `protocol_version` | string | Optional; capability hint (`ai_service` sends `1.0`). |
| `decisions` | array | Flat commands for `actions.apply_decisions()`. |

**Decision item** (flat — `parse_tick_response`):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "sim_id": 12345,
  "action": "go_home"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Echoed as `decision_id` in the **next** request’s `outcomes`. |
| `sim_id` | integer or string | Target Sim id (mod parses with `int(str(sim_id))`). |
| `action` | string | Registered handler in the mod (`registry.py`). |

The viewer WebSocket `type: "command"` message is validated as `ViewerCommandWsSchema` (**only** `type`, `action`, `sim_id`; extras are rejected); the server assigns `id` and the game sees the flat **decision item** above (`id`, `sim_id`, `action` only).

**Supported actions**

| `action` | Behaviour |
|----------|-----------|
| `go_home` | Push go-home affordance (`SIM_SKEWER_AFFORDANCES[0]`) at high priority. |
| `summon_sim` | Off-lot Sim: `active_venue.summon_npcs` (`NPCSummoningPurpose.DEFAULT` or `BRING_PLAYER_SIM_TO_LOT`). No-op if already instanced. |

Unknown `action` yields a failure outcome (`unknown action …`).

### Transport errors & policy

| Situation | Handling |
|-----------|----------|
| Socket I/O failure, close frame | Mod drops the session and reconnects on the next flush. |
| Response not valid JSON / not an object | Mod logs, drops session. |
| Server internal error mid-stream | Prefer close with an appropriate WebSocket close code after last valid response where possible; mod reconnects next tick. |

## Client behaviour (mod)

- **Timeouts:** Bounded read/write/connect timeouts so a hung peer does not stall gameplay indefinitely.
- **Ping/pong:** Act on server **ping** frames with **pong** (RFC **6455**); standard library stack does framing only.
- **TLS:** Hosted `wss:` must use sane certificate verification (document dev-only skips if you need them).

## Server implementation notes (FastAPI)

- Register **`GET /v1/tick`** upgraded to **`WebSocket`**, validating each inbound text payload with **`TickRequestSchema`** and emitting **`TickResponseSchema`** serialized with `model_dump_json()`.
- **`uvicorn`**: e.g. **`uvicorn ai_service.__main__:app --host 127.0.0.1 --port 8765`**.
- **CORS:** Not required for the game client; browser viewer still uses its own origins as today.

## Changelog

| Version | Change |
|---------|--------|
| 2.0 | Tick bridge is **`WebSocket /v1/tick` only**: JSON request/response as single text frames; persistent connection per loaded zone session. |
