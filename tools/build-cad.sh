#!/usr/bin/env bash
# All CAD: extracts the meshes, runs cad/freecad/build.py in freecadcmd. About a minute.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FREECADCMD="${FREECADCMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}"
cd "$ROOT"
if [[ -f cad/vendor/ugrinsky/Ugrinsky_Wind_Turbine.3mf ]]; then
  uv run vawt import-turbine >/dev/null
else
  echo "no 3MF in cad/vendor/ugrinsky: building without the rotor (see its README)"
fi
LOG="$ROOT/build/cad/freecad.log"
mkdir -p "$(dirname "$LOG")"
# freecadcmd exits 0 even when the script raises: the log decides
VAWT_ROOT="$ROOT" "$FREECADCMD" -c "exec(open('$ROOT/cad/freecad/build.py').read())" >"$LOG" 2>&1 || true
if grep -q 'Traceback' "$LOG" || ! grep -q 'wrote .*wind-turbine.FCStd' "$LOG"; then
  grep -av ' %)' "$LOG" | tail -30
  echo "cad/freecad/build.py did not finish"
  exit 1
fi
grep -E '^wrote' "$LOG"
