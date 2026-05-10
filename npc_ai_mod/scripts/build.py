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
"""

import argparse
import os
import shutil
import sys
import zipfile

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "npc_ai_mod")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
ARCHIVE_NAME = "npc_ai_mod.ts4script"
ARCHIVE_PATH = os.path.join(DIST_DIR, ARCHIVE_NAME)

# Override via env var or edit this path for your machine.
MODS_DIR = os.environ.get(
    "SIMS4_MODS_DIR",
    os.path.expanduser("~/Documents/Electronic Arts/The Sims 4/Mods"),
)

EXCLUDE_PATTERNS = ("__pycache__", ".pyc", ".pyo", ".mypy_cache", ".log")


def _should_exclude(path: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if pat in path:
            return True
    return False


def build() -> None:
    os.makedirs(DIST_DIR, exist_ok=True)

    if not os.path.isdir(SRC_DIR):
        print(f"[error] Source directory not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    with zipfile.ZipFile(ARCHIVE_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(SRC_DIR):
            dirnames[:] = [d for d in dirnames if not _should_exclude(d)]
            for filename in filenames:
                if _should_exclude(filename):
                    continue
                abs_path = os.path.join(dirpath, filename)
                # arcname keeps npc_ai_mod/ at the archive root.
                arcname = os.path.relpath(abs_path, os.path.dirname(SRC_DIR))
                zf.write(abs_path, arcname)

    size_kb = os.path.getsize(ARCHIVE_PATH) / 1024
    print(f"[build] {ARCHIVE_PATH}  ({size_kb:.1f} KB)")


def deploy() -> None:
    if not os.path.isdir(MODS_DIR):
        print(f"[error] Mods directory not found: {MODS_DIR}", file=sys.stderr)
        print(
            "        Set SIMS4_MODS_DIR or edit MODS_DIR in scripts/build.py",
            file=sys.stderr,
        )
        sys.exit(1)
    dest = os.path.join(MODS_DIR, ARCHIVE_NAME)
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
    args = parser.parse_args()

    build()
    if args.deploy:
        deploy()


if __name__ == "__main__":
    main()
