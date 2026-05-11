#!/usr/bin/env python3
"""
build.py — package npc_ai_mod/ into a deployable .ts4script archive.

A .ts4script file is a ZIP archive that the Sims 4 engine loads directly from
the Mods folder.  The package directory must sit at the root of the archive so
the game can import it as `npc_ai_mod`.

Usage
-----
    python scripts/build.py [--deploy]

Options
-------
--deploy    Copy the built archive to the Sims 4 Mods folder after packaging.
            Set the SIMS4_MODS_DIR environment variable or edit MODS_DIR below.

Output
------
    dist/npc_ai_mod.ts4script

Profiles
--------
    Bake ``npc_ai_mod/config/generated.py`` from ``config/profiles/<name>.py``:

        python scripts/build.py --profile production
        python scripts/build.py --profile development --deploy

    Default profile is ``production``.
"""

import argparse
import os
import shutil
import sys
import zipfile
from zipfile import PyZipFile

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "npc_ai_mod")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
ARCHIVE_NAME = "npc_ai_mod.ts4script"
ARCHIVE_PATH = os.path.join(DIST_DIR, ARCHIVE_NAME)

CONFIG_PKG = os.path.join(SRC_DIR, "config")
PROFILE_DIR = os.path.join(CONFIG_PKG, "profiles")
GENERATED_CONFIG = os.path.join(CONFIG_PKG, "generated.py")


def materialize_build_config(profile: str) -> None:
    """Copy profiles/<profile>.py → config/generated.py."""
    src = os.path.join(PROFILE_DIR, f"{profile}.py")
    if not os.path.isfile(src):
        print(f"[error] Unknown profile or missing file: {src}", file=sys.stderr)
        sys.exit(1)
    shutil.copy2(src, GENERATED_CONFIG)
    rel = os.path.relpath(GENERATED_CONFIG, PROJECT_ROOT)
    print(f"[build] config profile {profile!r} → {rel}")

# Override via env var or edit this path for your machine.
MODS_DIR = os.environ.get(
    "SIMS4_MODS_DIR",
    os.path.expanduser("~/Documents/Electronic Arts/The Sims 4/Mods"),
)

def build() -> None:
    os.makedirs(DIST_DIR, exist_ok=True)

    if not os.path.isdir(SRC_DIR):
        print(f"[error] Source directory not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    # PyZipFile.writepy compiles .py → .pyc under the running Python version
    # (must be 3.7 — use `uv run python scripts/build.py`) and stores them with
    # full archive-relative paths so __file__ inside the zip includes the archive path.
    with PyZipFile(ARCHIVE_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writepy(SRC_DIR)

    size_kb = os.path.getsize(ARCHIVE_PATH) / 1024
    print(f"[build] {ARCHIVE_PATH}  ({size_kb:.1f} KB)")
    with zipfile.ZipFile(ARCHIVE_PATH) as zf:
        for name in sorted(zf.namelist()):
            print(f"  {name}")


def deploy() -> None:
    if not os.path.isdir(MODS_DIR):
        print(f"[error] Mods directory not found: {MODS_DIR}", file=sys.stderr)
        print(
            "        Set SIMS4_MODS_DIR or edit MODS_DIR in scripts/build.py",
            file=sys.stderr,
        )
        sys.exit(1)
    dest_dir = os.path.join(MODS_DIR, "npc_ai_mod")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, ARCHIVE_NAME)
    shutil.copy2(ARCHIVE_PATH, dest)
    print(f"[deploy] Copied to {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build (and optionally deploy) npc_ai_mod."
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Copy the built archive to the Sims 4 Mods folder after packaging.",
    )
    parser.add_argument(
        "--profile",
        choices=("development", "production"),
        default="production",
        help="Bake config from config/profiles/<profile>.py into config/generated.py",
    )
    args = parser.parse_args()

    materialize_build_config(args.profile)
    build()
    if args.deploy:
        deploy()


if __name__ == "__main__":
    main()
