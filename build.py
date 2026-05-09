#!/usr/bin/env python3
"""
build.py — cross-platform build and deploy script for npc_ai_mod.

Works on Windows, Linux, and macOS.
Reads MODS_DIR from .env (copy .env.example -> .env and fill it in).

Usage:
  python build.py               # compile + deploy
  python build.py --compile-only  # compile only, skip deploy
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
MOD_NAME = "npc_ai_mod"
SCRIPT = f"{MOD_NAME}.ts4script"


def load_dotenv(path: Path) -> None:
    """Parse a .env file and inject variables into os.environ (if not already set)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if key and key not in os.environ:
            os.environ[key] = val


def find_python37() -> "list[str] | None":
    """Return an argv prefix for Python 3.7, or None if not found."""
    candidates: list[list[str]] = [
        ["python3.7"],
        ["python3", "-c", "import sys; assert sys.version_info[:2]==(3,7)"],
    ]
    if sys.platform == "win32":
        candidates = [["py", "-3.7"]] + candidates

    for argv in candidates:
        try:
            check = (
                argv[:1] + ["--version"]
                if argv[1:] != ["-c", "import sys; assert sys.version_info[:2]==(3,7)"]
                else argv[:1] + ["-V"]
            )
            out = subprocess.check_output(
                argv[0:1]
                + (argv[1:2] if len(argv) > 1 and argv[1] != "-c" else ["--version"]),
                stderr=subprocess.STDOUT,
                text=True,
            )
            if "3.7" in out:
                return argv[0:1] if len(argv) == 1 else argv[:2]
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return None


def compile_mod(py37: "list[str]") -> None:
    script = f"""
import sys, zipfile
from zipfile import PyZipFile

mod = "{MOD_NAME}"
out = "{SCRIPT}"

with PyZipFile(out, "w") as z:
    z.writepy(mod)

with zipfile.ZipFile(out) as z:
    names = z.namelist()

if not any(n.endswith(".pyc") for n in names):
    print("ERROR: no .pyc files in archive")
    sys.exit(1)

print("  " + out + " contains:")
for n in sorted(names):
    print("    " + n)
"""
    cmd = py37 + ["-c", script]
    subprocess.check_call(cmd, cwd=str(ROOT))


def deploy_mod(mods_dir: str) -> None:
    src = ROOT / SCRIPT
    dst = Path(mods_dir) / SCRIPT
    shutil.copy2(src, dst)
    print(f"  -> {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Build {MOD_NAME}")
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Compile only; skip copying to Mods folder",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    # ── Python 3.7 check ─────────────────────────────────────────────────────
    py37 = find_python37()
    if py37 is None:
        print("ERROR: Python 3.7 not found.")
        print("  Linux (Arch):  yay -S python37")
        print("  Linux (Deb):   sudo apt install python3.7")
        print("  Windows:       https://www.python.org/downloads/release/python-3718/")
        sys.exit(1)

    # ── Compile ──────────────────────────────────────────────────────────────
    version = subprocess.check_output(
        py37 + ["--version"], stderr=subprocess.STDOUT, text=True
    ).strip()
    print(f"Compiling {MOD_NAME} with {version}...")
    compile_mod(py37)

    if args.compile_only:
        print("Done (compile only).")
        return

    # ── Deploy ───────────────────────────────────────────────────────────────
    mods_dir = os.environ.get("MODS_DIR", "").strip()
    if not mods_dir:
        print("\nMODS_DIR not set — skipping deploy.")
        print("Copy .env.example to .env and set MODS_DIR to deploy automatically.")
        return

    if not Path(mods_dir).is_dir():
        print(f"ERROR: MODS_DIR does not exist: {mods_dir}")
        sys.exit(1)

    print("Deploying to Mods...")
    deploy_mod(mods_dir)
    print("\nDone. Restart the game and load a save.")


if __name__ == "__main__":
    main()
