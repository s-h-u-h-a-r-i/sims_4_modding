# Agent guide — Sims 4 NPC AI modding

This document is for coding agents (and humans) working in this repository. Read it before changing the mod, service, or stubs.

## Maintainer stance

**I fucking despise shortcuts in any form.** That is binding policy here: no convenience-typing dumps (`typing.Any`, unstructured `dict` blobs) where a real schema or **`PROTOCOL.md`** shape exists; no guessing game APIs without **`EA/`** precedent; no “temporary” wideners or “we’ll tighten it later.” Ship the disciplined version—narrow types, explicit wire models at boundaries, stubs that say what things are—unless I explicitly sign off on a deliberate trade-off in chat.

## Repository layout

| Area | Path | Role |
|------|------|------|
| **Game mod** | `npc_ai_mod/` | Python 3.7 script mod: hooks the game, snapshots world state, applies decisions over the **`WebSocket`** tick bridge. Packaged for installation into the game's `Mods` folder. |
| **AI / viewer service** | `ai_service/ai_service/` | FastAPI app: **`WebSocket /v1/tick`** from the game, separate viewer WebSocket, command queue. Not the game runtime. |
| **Decompiled EA scripts** | `EA/simulation/` | Read-only reference for how the retail game implements APIs. Prefer grep/search here before inventing behavior. |
| **Type stubs** | `stubs/` | `.pyi` models for game-provided modules (`services`, `distributor`, `sims`, …). Consumed via `npc_ai_mod/pyproject.toml` `extraPaths` and repo `setup.cfg` `mypy_path`. |
| **Protocol** | `PROTOCOL.md` | WebSocket JSON message shapes and decisions shared by mod and service. |

The editor may open **`sims_4_modding`**, **`npc_ai_mod`**, and **`ai_service`** as separate workspace roots; paths above are relative to `sims_4_modding` unless a subproject says otherwise.

## Runtime constraints

- The **mod** runs inside **The Sims 4** (Python **3.7**). Do not use 3.8+ syntax in mod code unless you have a clear compatibility story.
- Imports such as `services`, `distributor`, `sims`, `interactions` come from the **game**, not PyPI. If something is missing from the type checker, add or extend **`stubs/`**, do not add fake runtime packages.

## Stubs (`stubs/`) — no “quick sketches”

Stubs exist so editors and Pyright/mypy can verify mod code **without** pretending the full game is importable locally.

When you add or change game-facing APIs in stubs:

1. **Ground types in EA or known call sites.** Open `EA/simulation/` (or existing mod handlers) and match parameters and return behavior. Name tunings and protobuf-shaped tuples after what EA uses (comments are encouraged).
2. **Do not reach for `typing.Any` as a default.** Use the narrowest accurate type: concrete classes, `Union`/`Tuple`, `Protocol`, or `object` for “some game object we do not model yet.” Reserve `Any` for genuinely opaque data (rare).
3. **Prefer explicit wire shapes** for distributor ops, tuning ids, and fixed-length protobuf fields (e.g. four-int summon blobs) over vague `Sequence` when the game is strict.
4. **Avoid churn:** add only what callers need; do not copy entire decompiled modules into stubs.

If a type is unknowable, document *why* in a one-line comment and use `object` or a small `Protocol`, not a blanket `Any`.

## Implementing mod behavior

- **Find precedent in `EA/simulation/`** (e.g. `Venue.summon_npcs` / `NPCSummoningPurpose`, travel, interactions) before writing new engine calls.
- **Handlers** live under `npc_ai_mod/npc_ai_mod/actions/handlers/` and are registered in `actions/registry.py` with the exact **wire action** string the service sends.
- **Viewer commands** flow: viewer WebSocket → tick store → **`decisions`** on the next **`/v1/tick`** server reply → mod `actions.apply_decisions`. Keep action names in sync between viewer JS and `ACTION_HANDLERS`.

## AI service and viewer

- Python version and dependencies follow **`ai_service/ai_service`** packaging (not necessarily 3.7).
- Static viewer assets live under `ai_service/ai_service/static/viewer/`. Preserve existing patterns for commands and history.

## What not to do

- Do not treat `EA/` as something to “sync” back into the game; it is a decompiled reference only.
- Do not expand scope with drive-by refactors or unsolicited markdown files; the user will ask when they want docs updated.

## Checklist before finishing a change

- [ ] Mod code stays Python 3.7–compatible where it ships to the game.
- [ ] New game imports have appropriate **`stubs/`** updates with **specific** types.
- [ ] New tick actions are registered and named consistently with **`ai_service`** if viewer-related.
- [ ] Behavior matches an **EA precedent** or is explicitly documented when experimental.
