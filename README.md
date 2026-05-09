# npc_ai_mod

A Sims 4 script mod that bridges the game to an external AI service, enabling
AI-driven control of NPC Sims.

## How it works

1. After a save loads, the mod collects NPC Sim state (traits, motives, location, etc.)
2. It sends that state to a local AI service over HTTP
3. The AI service returns decisions (which interactions to perform)
4. The mod pushes those interactions onto the target Sims

The in-game mod (`npc_ai_mod/`) and the AI service are separate — you can run
any AI backend you like as long as it speaks the bridge protocol.

## Requirements

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.7.x | Compile mod bytecode (must match game's Python) |
| Python | any modern | Run `build.py` / tooling |
| pycdc | latest | Decompile EA scripts for IDE type support |
| The Sims 4 | any | Game |

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/your-username/npc_ai_mod
cd npc_ai_mod
cp .env.example .env
```

Open `.env` and fill in your paths:

- `MODS_DIR` — absolute path to your Sims 4 `Mods` folder
- `GAME_DIR` — absolute path to the Sims 4 `Data/Simulation/Gameplay` folder

### 2. Install Python 3.7

The game runs Python 3.7, so mod bytecode must be compiled with it.

| Platform | Command |
|---|---|
| Arch Linux | `yay -S python37` |
| Ubuntu/Debian | `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.7` |
| Windows | [python.org/downloads](https://www.python.org/downloads/release/python-3718/) |

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

**Linux/macOS:**
```bash
./build.sh
```

**Windows or any platform:**
```bash
python build.py
```

Both scripts compile `npc_ai_mod/` into `npc_ai_mod.ts4script` and copy it to
your `MODS_DIR`. If `MODS_DIR` is not set they compile only and skip the copy.

## Project structure

```
npc_ai_mod/
  __init__.py    — entry point, registers game hooks
  hooks.py       — VenueService injection (fires after each save loads)
  sim_state.py   — read and serialize NPC Sim data
  bridge.py      — HTTP client to the external AI service
  director.py    — apply AI decisions onto NPC Sims
build.sh         — Linux/macOS build script
build.py         — cross-platform build script
decompile_ea.sh  — extract + decompile EA scripts for IDE support
.env.example     — environment variable template
pyrightconfig.json — Pyright config (points to EA/ for type resolution)
```

## Contributing

Fork the repo, create a branch, and open a pull request. The AI service
protocol (what `bridge.py` sends/receives) will be documented in `PROTOCOL.md`
once it stabilises.

## Notes

- Mods must be enabled in the game options (`Game Options > Other > Enable Custom Content and Mods`)
- After deploying, restart the game fully — the game caches mod scripts
- The mod targets game version 1.x (Python 3.7 bytecode, magic number 3394)
