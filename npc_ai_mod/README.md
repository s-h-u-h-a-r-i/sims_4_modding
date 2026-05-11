# npc_ai_mod

A Sims 4 Python mod that hooks the game engine and streams world state to a
local AI service, then applies decisions (like sending NPCs home) back onto Sims
in real time.

## How it works

1. The mod monkey-patches two game engine methods (`VenueService` and `Zone`) to
   detect when a zone loads or unloads.
2. A repeating probe alarm fires every 0.75 s, taking a cheap
   "activity fingerprint" of every instanced Sim's running and queued
   interactions (noise classes such as idle overlays are excluded).
3. When the fingerprint changes (confirmed across two consecutive probes), a
   debounce timer arms. After 0.35 s of quiet the mod POSTs the full world
   snapshot to the AI service at `http://127.0.0.1:8765/v1/tick`.
4. The AI service responds with a list of decisions; the mod applies each one
   (currently supports `go_home`).

See [docs/architecture.md](docs/architecture.md) for a detailed module breakdown
and data-flow diagrams.

## Project structure

```
npc_ai_mod/
├── npc_ai_mod/           # mod source package (deployed as .ts4script)
│   ├── __init__.py
│   ├── hooks.py          # game-engine monkey-patches
│   ├── director.py       # probe/debounce/tick orchestration
│   ├── bridge.py         # HTTP client → ai_service
│   ├── sim_state.py      # game-state readers & fingerprinting
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

- **In-game runtime:** Python 3.7 (embedded in Sims 4 — no external packages).
- **Development:** any modern Python for the build script.

## Development setup

```bash
uv sync --extra dev   # installs pytest into the venv
uv run pytest         # run all tests
```

## Building and deploying

```bash
# Build only
python scripts/build.py

# Build and copy to your Mods folder
python scripts/build.py --deploy

# Override the default Mods path
SIMS4_MODS_DIR="/path/to/Mods" python scripts/build.py --deploy
```

The output archive is written to `dist/npc_ai_mod.ts4script`.

Enable **Script Mods** in the Sims 4 game options, then drop the archive into
your Mods folder (one subfolder deep is fine).

## Logging

Debug lines wait in a short in-memory staging list until the next `/v1/tick`
POST is built: up to **250** entries are drained into the JSON `logs` field per
request, then removed from the mod (there is **no retry** if the POST fails;
long-lived storage is the viewer **localStorage**). If the bridge stays down,
the staging list truncates at **500** oldest-first. Levels: `debug`, `info`,
`error`. The staging list clears when the script package reloads.

The legacy `npc_ai_mod.log` file is no longer used.

## AI service

The companion service lives in `../ai_service/`. It must be running on
`127.0.0.1:8765` before loading a save.
