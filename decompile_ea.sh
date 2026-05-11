#!/usr/bin/env bash
# Extracts and decompiles the Sims 4 EA Python scripts for IDE type support.
# Uses pycdc which handles EA's Python 3.7 bytecode correctly.
#
# Skips base.zip — it only contains stdlib copies; Pyright has those already.
# Skips individual files that crash pycdc and reports them at the end.
#
# Output: EA/core/  EA/simulation/
# Run once after setup; re-run after game patches.
#
# Reads GAME_DIR from npc_ai_mod/.env (copy npc_ai_mod/.env.example → npc_ai_mod/.env).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Load npc_ai_mod/.env ─────────────────────────────────────────────────────
if [[ -f "${SCRIPT_DIR}/npc_ai_mod/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/npc_ai_mod/.env"
  set +a
fi

GAME_DIR="${GAME_DIR:-}"
OUT="EA"

# ── Preflight ────────────────────────────────────────────────────────────────
if ! command -v pycdc &>/dev/null; then
  echo "ERROR: pycdc not found."
  echo "  Arch Linux:  yay -S pycdc"
  echo "  From source: https://github.com/zrax/pycdc"
  exit 1
fi

if [[ -z "${GAME_DIR}" ]]; then
  echo "ERROR: GAME_DIR not set."
  echo "Copy npc_ai_mod/.env.example to npc_ai_mod/.env and set GAME_DIR."
  exit 1
fi

for zip in core simulation; do
  if [[ ! -f "${GAME_DIR}/${zip}.zip" ]]; then
    echo "ERROR: ${GAME_DIR}/${zip}.zip not found"
    exit 1
  fi
done

# ── Extract ──────────────────────────────────────────────────────────────────
rm -rf "${OUT}/base"  # not needed — Pyright has stdlib stubs already

echo "Extracting game scripts (core + simulation only)..."
for zip in core simulation; do
  dest="${OUT}/${zip}"
  rm -rf "${dest}"
  python3 -m zipfile -e "${GAME_DIR}/${zip}.zip" "${dest}"
  count=$(find "${dest}" -name "*.pyc" | wc -l)
  echo "  ${zip}.zip → ${dest}/ (${count} .pyc files)"
done

# ── Decompile ────────────────────────────────────────────────────────────────
mapfile -t pyc_files < <(find "${OUT}" -name "*.pyc" -type f | sort)
total=${#pyc_files[@]}
echo ""
echo "Decompiling ${total} files..."

failed=()
for i in "${!pyc_files[@]}"; do
  f="${pyc_files[$i]}"
  out="${f%.pyc}.py"
  n=$((i + 1))

  printf "\r  [%d/%d] %-60s" "${n}" "${total}" "${f##*/EA/}"

  pycdc "${f}" > "${out}" 2>/tmp/pycdc_err || true

  if [[ ! -s "${out}" ]]; then
    failed+=("${f}")
    rm -f "${out}"
  fi
done

echo ""
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
py_count=$(find "${OUT}" -name "*.py" | wc -l)
fail_count=${#failed[@]}

echo "Done. ${py_count} files decompiled, ${fail_count} skipped."

if [[ ${fail_count} -gt 0 ]]; then
  echo ""
  echo "Skipped files (pycdc could not decompile):"
  for f in "${failed[@]}"; do
    echo "  ${f}"
  done
fi

echo ""
echo "Pyright resolves:"
echo "  from sims4 import commands, log    →  EA/core/sims4/"
echo "  import services                    →  EA/simulation/services/"
echo "  import zone                        →  EA/simulation/zone.py"
echo "  from sims.sim_info import SimInfo  →  EA/simulation/sims/sim_info.py"
