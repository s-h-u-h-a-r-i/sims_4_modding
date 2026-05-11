# Architecture

## Overview

`npc_ai_mod` is a Sims 4 Python mod that bridges the game engine and a local AI
service running on `127.0.0.1:8765`.  On each meaningful world-state change it
POSTs a JSON payload (`/v1/tick`) describing all instanced Sims and receives
back a list of decisions the AI wants applied (e.g. send a Sim home).

```
┌─────────────────────────────────────────────────────┐
│                  Sims 4 Game Engine                 │
│                                                     │
│  VenueService.on_loading_screen_animation_finished  │
│  Zone.on_teardown           (monkey-patched)        │
│        │                          │                 │
│        ▼                          ▼                 │
│   hooks.py ──────────────► director.py              │
│                              │                      │
│               probe alarm ───┘ (every 0.75 s)       │
│               debounce alarm (0.35 s quiet)         │
│                              │                      │
│                              ▼                      │
│                         bridge.py                   │
│                    POST /v1/tick (HTTP)              │
└────────────────────────┬────────────────────────────┘
                         │  JSON payload
                         ▼
              ┌─────────────────────┐
              │  ai_service         │
              │  127.0.0.1:8765     │
              │  /v1/tick           │
              └──────────┬──────────┘
                         │  {"decisions": [...]}
                         ▼
                    director.py
                 apply_decisions()
                    go_home, ...
```

---

## Module Responsibilities

### `hooks.py`
Monkey-patches two game-engine methods at import time:

| Patched method | Trigger |
|---|---|
| `VenueService.on_loading_screen_animation_finished` | Zone finished loading |
| `Zone.on_teardown` | Zone is being unloaded |

Both delegate to `director.on_zone_loaded()` / `director.on_zone_unloaded()`.
No game-state reads happen here — all logic lives in `Director`.

### `director.py`
The central orchestrator.  A single `Director` singleton is created at module
load and lives for the lifetime of the game session.

**Probe loop** — a repeating real-time alarm fires every `_PROBE_REAL_SECONDS`
(0.75 s) and calls `world_activity_fingerprint_if_stable()`.  The fingerprint is
a cheap hashable tuple:

1. **`zone_id`**, **`lot_id`**
2. Per-instanced Sim: sorted `(sim_id, running_class_multiset,
   queued_class_multiset)` — affordance **`__class__.__name__`** counts, excluding
   idle / passive noise (see fingerprint noise section below).
3. **Partner-wire attachment** — sorted `(sim_id → sorted partner sim_ids)` matching
   the **`social_partner_sim_ids`** merged onto the outbound tick (SI-derived links
   plus shared non-Sim object cohorts).

If multisets alone are unchanged but co-presence wiring changes (e.g. chat ends
but two Sims remain on the same stereo), component (3) still dirties so the bridge
gets a POST and the viewer clears stale chips.

**Debounce** — two consecutive dirty probes arm a 0.35 s one-shot alarm.  If
the world goes quiet the debounce fires and a POST is sent.

**Max-wait** — if the world churns continuously for > 4 s the director forces a
POST regardless.

**Idle keepalive** — if nothing changes for > 5 s the director sends a POST so
that viewer commands queued server-side are delivered promptly.

**Rate limiting** — a 1.25 s minimum interval between consecutive POSTs
prevents tight POST → dirty → POST loops.

### `bridge.py`
Thin HTTP client.  Opens a new `http.client.HTTPConnection` per call (the Sims
4 engine does not support async I/O and the call is short-lived).  Returns the
parsed JSON dict on HTTP 200, `None` on any error.

| Constant | Value |
|---|---|
| `HOST` | `127.0.0.1` |
| `PORT` | `8765` |
| `PATH` | `/v1/tick` |
| `TIMEOUT_SEC` | `5` |

### `config/`
Runtime constants are chosen at **package time**:

- **`config/profiles/production.py`** — quiet staging list, **`MOD_LOG_DRAIN_PER_TICK`**
  modest, chunked SI dumps **off**.
- **`config/profiles/development.py`** — large drain + staging cap + **`VERBOSE_SIM_INTERACTION_DUMP`**.
- **`config/generated.py`** — copied from one profile by **`build.py`** /
  **`scripts/build.py --profile …`** before compiling. Missing file → import falls back
  to **`profiles/production`**.

`director` reads **`MOD_LOG_DRAIN_PER_TICK`**; **`sim_state`** reads **`VERBOSE_…`** and **`LOG_STAGING_MAX`**.

### `sim_state.py`
Reads game state and converts it to plain Python dicts safe for JSON
serialisation.

- **`get_instanced_sim_infos()`** — returns only Sims physically present in the
  zone.
- **`serialize_sim()`** — id, name, age, gender, household/zone ids, running/
  queued interactions, **`social_partner_sim_ids`** from SI-derived participants
  (logged in **`SI_DUMP` prelude before** object cohort merge — prelude can show
  `[]` while wire lists still cohort-link via stereo, etc.).
- **`get_world_state()`** — applies **`_partner_graph_instanced_wire()`** cohort merge
  so payload **`social_partner_sim_ids`** include shared non-Sim targets.
- **`world_activity_fingerprint()`** — class multisets **plus partner-wire tuples**
  so cohort-only changes dirties probes.

Director helper **`_fingerprint_diff`** prints human deltas (including `"partner wire edges changed"`).

### `logutil.py`

Structured lines (`timestamp_utc`, `level`, `tag`, `message`, optional traceback)
land in an in-memory staging list. **`LOG_STAGING_MAX`** (profile) caps backlog;
 **`drain_logs_for_tick(MOD_LOG_DRAIN_PER_TICK)`** moves up to that many entries into
 **`logs`** per tick (values defined in **`config/generated.py`** for the baked profile;
 production defaults: drain 250, staging cap 500). Viewer holds durable history; the mod drops drained lines regardless of HTTP success.

Functions: `clear_session_log`, `drain_logs_for_tick`, `log_debug`, `log_info`,
`log_error`.

### `utils.py`
Single helper: `iso_utc_now()` returns the current UTC time as an ISO 8601
string.

---

## Data Flow — Tick Payload

```json
{
  "tick": {
    "id": 42,
    "timestamp_utc": "2026-05-10T19:15:00.123456+00:00"
  },
  "world": {
    "zone_id": 123456789,
    "lot_id": 987654321,
    "sims": [
      {
        "sim_id": 111,
        "sim_id_str": "111",
        "first_name": "Alice",
        "last_name": "Smith",
        "age": "ADULT",
        "gender": "FEMALE",
        "is_npc": true,
        "household_id": 222,
        "zone_id": 123456789,
        "interactions_running": [
          {"interaction_id": 1, "interaction_id_str": "1", "class_name": "EatFood_Dine"}
        ],
        "interactions_queue": [],
        "social_partner_sim_ids": ["9876543210"]
      }
    ]
  },
  "outcomes": [
    {
      "decision_id": "b1d2e3f4-...",
      "status": "failure",
      "reason": "unknown action 'foo'"
    }
  ],
  "logs": [
    {
      "timestamp_utc": "2026-05-10T19:15:00.100000+00:00",
      "level": "info",
      "tag": "Director",
      "message": "debounce timer fired: attempting POST after quiet period",
      "traceback": null
    }
  ]
}
```

Per-Sim **`social_partner_sim_ids`** are stringified bigint ids on the wire (avoid JSON
precision loss). They merge explicit SI social-thread participants with Sims sharing
the same non-Sim interaction target where applicable.

Keys `outcomes` and `logs` are omitted when empty (`schemas.tick_payload_to_wire`).

## Data Flow — Decision Response

```json
{
  "protocol_version": "1.0",
  "decisions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "sim_id": 111,
      "action": "go_home"
    }
  ]
}
```

The `id` is assigned by `ai_service` when a command is queued; the mod echoes it as `decision_id` in the next tick’s `outcomes`.

Supported actions:

| Action | Effect |
|---|---|
| `go_home` | Pushes `SIM_SKEWER_AFFORDANCES[0]` (go-home interaction) at `Priority.High` |

---

## Fingerprint Noise Exclusion

The following affordance classes are excluded from the activity fingerprint to
avoid spurious ticks caused by engine background loops:

| Excluded | Reason |
|---|---|
| `Emotion_Idle` | Emotional idle overlay cycles constantly |
| `stand_Passive` | Standing idle, ticks every few frames |
| `sit_Passive` | Seated idle |
| `SocialPickerSI` | Social picker engine loop (~1.5 s cycle) |
| `Idle_*` | Age/mood idle overlays |
| `idle_*` | Lifestyle idle variants |
| `aggregate_*` | Background observation callbacks |
These exclusions affect **SI class multiset** rows inside `world_activity_fingerprint()` only.
The fingerprint’s separate **partner-wire** component (`sim_id → partner ids`) is not filtered here.

## Deployment

The mod is distributed as a `.ts4script` archive (a ZIP file).  Build with:

```bash
python scripts/build.py --profile production   # default
python scripts/build.py --profile development  # baked verbose SI dumps
python scripts/build.py --deploy
```

From repo root (parent of `npc_ai_mod/`): **`python build.py --profile …`** does the same
and writes **`npc_ai_mod.ts4script`** next to **`build.py`**.

Set `SIMS4_MODS_DIR` or `MODS_DIR` (depending on script) per each script’s README.
