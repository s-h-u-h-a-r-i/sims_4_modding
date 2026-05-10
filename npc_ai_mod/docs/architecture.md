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
(0.75 s) and calls `world_activity_fingerprint_if_stable()`.  The fingerprint
is a cheap hashable tuple of (zone_id, lot_id, per-sim affordance-class
multisets).

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

### `sim_state.py`
Reads game state and converts it to plain Python dicts safe for JSON
serialisation.

- **`get_instanced_sim_infos()`** — returns only Sims physically present in the
  zone.
- **`serialize_sim()`** — id, name, age, gender, household/zone ids, running and
  queued super-interactions.
- **`world_activity_fingerprint()`** — affordance-class multisets, excluding
  noise classes (idle overlays, passive stances, social picker engine loops).
- **`fingerprint_diff()`** — human-readable delta for debug logging.

### `logutil.py`
File logger that writes beside the `.ts4script` archive (or beside the package
directory when running loose scripts during development).  Four functions:
`clear_session_log`, `log_debug`, `log_info`, `log_error`.

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
        "interactions_queue": []
      }
    ]
  }
}
```

## Data Flow — Decision Response

```json
{
  "decisions": [
    {"action": "go_home", "sim_id": 111}
  ]
}
```

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
| `reactions_*` | Reaction overlays that flicker on/off |

---

## Deployment

The mod is distributed as a `.ts4script` archive (a ZIP file).  Build with:

```bash
python scripts/build.py           # writes dist/npc_ai_mod.ts4script
python scripts/build.py --deploy  # also copies to the Sims 4 Mods folder
```

Set `SIMS4_MODS_DIR` in your environment to point to your Mods directory if it
differs from the default (`~/Documents/Electronic Arts/The Sims 4/Mods`).
