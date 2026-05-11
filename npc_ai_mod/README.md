# npc_ai_mod

A Sims 4 Python mod that hooks the game engine and streams world state to a
local AI service, then applies decisions (like sending NPCs home) back onto Sims
in real time.

## How it works

1. The mod monkey-patches two game engine methods (`VenueService` and `Zone`) to
   detect when a zone loads or unloads.
2. A repeating probe alarm fires every 0.75 s, hashing **activity fingerprints**
   (running/queued affordance multisets — idle-style classes excluded — plus **partner-wire**
   tuples so co-presence can dirty probes without multiset churn).
3. When the fingerprint changes (confirmed across two consecutive probes), a
   debounce timer arms. After 0.35 s of quiet the mod sends the full world
   snapshot JSON over **`WebSocket ws://127.0.0.1:8765/v1/tick`** (persistent
   connection while the zone is loaded).
4. The AI service responds with decisions in the reply frame; the mod applies each one
   (currently supports `go_home`, `summon_sim`).

See [docs/architecture.md](docs/architecture.md) for a detailed module breakdown
and data-flow diagrams.

## Project structure

```
npc_ai_mod/
├── npc_ai_mod/           # mod source package (deployed as .ts4script)
│   ├── __init__.py
│   ├── config/           # profiles/ + generated.py (see Building)
│   ├── hooks/            # zone lifecycle monkey-patches (see hooks/zone_hooks.py)
│   ├── director.py       # probe/debounce/tick orchestration
│   ├── director_support.py  # real-time alarms + fingerprint debug diff
│   ├── bridge/           # WebSocket (`ws_tick.py`) + `constants.py`
│   │   ├── constants.py
│   │   └── ws_tick.py
│   ├── actions/          # apply server decisions (handlers + registry + dispatch)
│   │   ├── registry.py
│   │   ├── dispatch.py
│   │   └── handlers/
│   ├── schemas/          # tick/world dataclasses + JSON wire helpers
│   │   ├── models.py
│   │   └── wire.py
│   ├── sim_state/        # game state readers, fingerprinting, SI partner graph
│   │   ├── snapshot.py       # get_world_state, serialize_sim
│   │   ├── fingerprints.py   # world_activity_fingerprint*
│   │   ├── partner_wire.py   # cohort merge + partner wire slice of fingerprint
│   │   └── …                 # filters, iteration, partners, verbose SI dump, etc.
│   ├── logutil.py        # in-memory debug log shipped with ticks → viewer
│   └── utils.py          # UTC timestamp helper
├── scripts/
│   └── build.py          # packages npc_ai_mod/ into dist/npc_ai_mod.ts4script
├── docs/
│   └── architecture.md
├── pyproject.toml
└── CHANGELOG.md
```

## Requirements

- **In-game runtime:** Python 3.7 (embedded in Sims 4 — stdlib-only WebSocket framing in `bridge/ws_tick.py`).
- **Development:** any modern Python for the build script.

## Development setup

```bash
uv sync --extra dev   # installs pytest into the venv
uv run pytest         # run all tests
```

## Building and deploying

```bash
# Build only (default profile: production — see config/profiles/)
python scripts/build.py

# Verbose SI dumps + larger log drain per tick (development profile)
python scripts/build.py --profile development

# Build and copy to your Mods folder
python scripts/build.py --deploy

# Override the default Mods path (after setting MODS_DIR in npc_ai_mod/.env or the environment)
MODS_DIR="/path/to/Mods" python scripts/build.py --deploy
```

Each build copies `config/profiles/<profile>.py` to **`config/generated.py`**
(gitignored). If that file is missing, the mod falls back to production
constants at import time.

The output archive is written to `dist/npc_ai_mod.ts4script`.

Enable **Script Mods** in the Sims 4 game options, then drop the archive into
your Mods folder (one subfolder deep is fine).

## Logging

Debug lines wait in an in-memory staging list until the next outbound tick bundle is
built. Per tick, **`drain_logs_for_tick`** pulls at most **`MOD_LOG_DRAIN_PER_TICK`**
(from the active profile) into the JSON `logs` field, then removes them from the
mod (there is **no retry** if the bridge round-trip fails; long-lived storage is viewer
**localStorage**). **`LOG_STAGING_MAX`** caps backlog (oldest dropped first when
too many lines arrive before a successful flush). **`development`** raises both limits and
enables chunked **SI_DUMP** logging (heavy payloads).

Levels: `debug`, `info`, `error`. The staging list clears when the script reloads.

The legacy `npc_ai_mod.log` file is no longer used.

## AI service

The companion service lives in `../ai_service/`. It must be running on
`127.0.0.1:8765` before loading a save.
