#!/usr/bin/env bash
# Build and deploy npc_ai_mod on Linux/macOS.
# For Windows use build.py instead.
#
# Reads MODS_DIR from .env (copy .env.example → .env and fill it in).
set -euo pipefail

# ── Load .env ────────────────────────────────────────────────────────────────
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODS_DIR="${MODS_DIR:-}"
MOD_NAME="npc_ai_mod"
SCRIPT="${MOD_NAME}.ts4script"

# ── Preflight ────────────────────────────────────────────────────────────────
if ! command -v python3.7 &>/dev/null; then
  echo "ERROR: python3.7 not found."
  echo "  Arch Linux:  yay -S python37"
  echo "  Ubuntu/Deb:  sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.7"
  exit 1
fi

# ── Compile ──────────────────────────────────────────────────────────────────
echo "Compiling ${MOD_NAME} with $(python3.7 --version 2>&1)..."
python3.7 - <<'PYEOF'
import sys
from zipfile import PyZipFile
import zipfile

mod = "npc_ai_mod"
out = f"{mod}.ts4script"

with PyZipFile(out, "w") as z:
    z.writepy(mod)

with zipfile.ZipFile(out) as z:
    names = z.namelist()

if not any(n.endswith(".pyc") for n in names):
    print("ERROR: no .pyc files found in archive — compilation may have failed")
    sys.exit(1)

print(f"  {out} contains:")
for n in sorted(names):
    print(f"    {n}")
PYEOF

# ── Deploy ───────────────────────────────────────────────────────────────────
if [[ -z "${MODS_DIR}" ]]; then
  echo ""
  echo "MODS_DIR not set — skipping deploy."
  echo "Copy .env.example to .env and set MODS_DIR to deploy automatically."
  exit 0
fi

if [[ ! -d "${MODS_DIR}" ]]; then
  echo "ERROR: MODS_DIR does not exist: ${MODS_DIR}"
  exit 1
fi

echo "Deploying to Mods..."
cp "${SCRIPT}" "${MODS_DIR}/"
echo "  → ${MODS_DIR}/${SCRIPT}"

echo ""
echo "Done. Restart the game and load a save."
