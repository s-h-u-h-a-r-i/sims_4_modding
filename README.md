# npc_ai_mod

A Sims 4 script mod that bridges the game to an external AI service, enabling
AI-driven control of NPC Sims.

## How it works

1. After a save loads, the mod collects NPC Sim state (traits, motives, location, etc.)
2. It sends that state to a local AI service over **WebSocket** (`/v1/tick`)
3. The AI service returns decisions (which interactions to perform)
4. The mod pushes those interactions onto the target Sims

The in-game mod (`npc_ai_mod/`) and the AI service are separate — you can run
any AI backend you like as long as it speaks the bridge protocol.

## Requirements

| Tool       | Version | Purpose                                         |
| ---------- | ------- | ----------------------------------------------- |
| Python     | 3.7.x   | Compile mod bytecode (must match game's Python) |
| Python     | ≥ 3.10  | Run `ai_service` (FastAPI), `build.py`, tooling |
| pycdc      | latest  | Decompile EA scripts for IDE type support       |
| The Sims 4 | any     | Game                                            |

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/your-username/npc_ai_mod
cd npc_ai_mod                       # repository root: this folder contains npc_ai_mod/ and ai_service/
cp npc_ai_mod/.env.example npc_ai_mod/.env
```

Edit `npc_ai_mod/.env` and fill in your paths:

- `MODS_DIR` — absolute path to your Sims 4 `Mods` folder
- `GAME_DIR` — absolute path to the Sims 4 `Data/Simulation/Gameplay` folder

#### Cursor / VS Code

Pyright resolves `from ai_service...` **only when the workspace root is the repository directory** (so the `ai_service` package is visible). Prefer **Open Workspace from File…** → `npc-ai-mod.code-workspace`, or **Open Folder…** → repo root **not** single subfolders (`npc_ai_mod/` alone breaks those imports).

A multi-root workspace with **three roots** (`/`, `npc_ai_mod`, `ai_service`) is **discouraged** here: nesting duplicates paths and fights import resolution unless you rework `PYTHONPATH` per folder.

### 2. Install Python 3.7

The game runs Python 3.7, so mod bytecode must be compiled with it.

| Platform      | Command                                                                       |
| ------------- | ----------------------------------------------------------------------------- |
| Arch Linux    | `yay -S python37`                                                             |
| Ubuntu/Debian | `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.7`    |
| Windows       | [python.org/downloads](https://www.python.org/downloads/release/python-3718/) |

### 3. Set up IDE type support (optional but recommended)

Decompile EA's game scripts so your IDE (Cursor/VS Code with Pyright) can
resolve imports like `import services` and `from sims.sim_info import SimInfo`:

```bash
# Linux/macOS — requires pycdc (yay -S pycdc on Arch)
./decompile_ea.sh
```

Run this again after each game patch. The decompiled files go into `EA/` which
is gitignored.

### 4. Build and deploy

**Linux/macOS / Windows:**

```bash
cd npc_ai_mod
uv run python scripts/build.py                      # production profile (default)
uv run python scripts/build.py --profile development
uv run python scripts/build.py --deploy            # also copy to MODS_DIR
```

This bakes `npc_ai_mod/config/generated.py` from `config/profiles/<profile>.py` and writes `npc_ai_mod/dist/npc_ai_mod.ts4script`. `MODS_DIR` comes from the environment, from `npc_ai_mod/.env`, or defaults to the usual Electronic Arts Mods path; override it if yours differs.

### 5. Run the AI bridge (development)

Python 3.10+ recommended for the FastAPI process (separate from Python 3.7 used only to compile the mod).

```bash
cd ai_service
uv sync
uv run python -m ai_service.__main__
```

See [`ai_service/README.md`](ai_service/README.md).

## Project structure

```
npc_ai_mod/
  __init__.py    — entry point, registers game hooks
  hooks/         — VenueService / Zone monkey-patches (lazy `director` import)
  director.py    — probe/debounce / tick flush orchestration
  director_support.py — real-time alarms, fingerprint debug diff
  bridge/        — WebSocket tick client + constants to the external AI service
  actions/       — apply server decisions onto Sims (registry + handlers)
  schemas/       — tick/world dataclasses + JSON wire helpers
  sim_state/     — world snapshots, activity fingerprints, SI partner graph
ai_service/
  main.py / models.py / router_v1.py / game_types.py — FastAPI + EA type hints (see ai_service/README.md)
build.sh         — Linux/macOS build script
build.py         — cross-platform build script
decompile_ea.sh  — extract + decompile EA scripts for IDE support (reads GAME_DIR from npc_ai_mod/.env)
npc_ai_mod/.env.example — MODS_DIR + GAME_DIR template for build + decompile
ai_service/pyproject.toml — FastAPI service (use `uv` in `ai_service/`)
pyrightconfig.json — Pyright: repo root `.` + `EA/` on extraPaths; Python 3.7 vs 3.10 per subtree
.vscode/settings.json — Pylance `python.analysis.extraPaths` when opening the folder
npc-ai-mod.code-workspace — open this workspace (repo root — recommended)
PROTOCOL.md     — WebSocket bridge JSON between the mod and `ai_service`
```

## Contributing

Fork the repo, create a branch, and open a pull request. Keep
[`PROTOCOL.md`](PROTOCOL.md) in sync when changing request/response shapes.

## Notes

- Mods must be enabled in the game options (`Game Options > Other > Enable Custom Content and Mods`)
- After deploying, restart the game fully — the game caches mod scripts
- The mod targets game version 1.x (Python 3.7 bytecode, magic number 3394)
