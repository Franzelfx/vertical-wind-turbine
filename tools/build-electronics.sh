#!/usr/bin/env bash
# Schematic, ERC, first-pass board, 3D exports. About 20 seconds. Reports in build/reports/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KICAD_CLI="${KICAD_CLI:-$(command -v kicad-cli || echo /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli)}"
KICAD_PY="${KICAD_PY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}"
BOARD="$ROOT/electronics/charge-board"
OUT="$ROOT/build/kicad"
REPORTS="$ROOT/build/reports"
mkdir -p "$OUT" "$REPORTS"
cd "$ROOT"

uv run python electronics/charge-board/schematic/build.py
# KiCad on macOS prints harmless Fontconfig and NSCocoaError lines: its exit codes decide
"$KICAD_CLI" sch erc --severity-error --exit-code-violations --format json \
  -o "$REPORTS/erc.json" "$BOARD/charge-board.kicad_sch" >/dev/null 2>&1
"$KICAD_CLI" sch export netlist --format kicadxml -o "$OUT/charge-board.net.xml" \
  "$BOARD/charge-board.kicad_sch" >/dev/null 2>&1

uv run python -c "
import dataclasses, json
from vawt.spec import BOARD
print(json.dumps(dataclasses.asdict(BOARD)))" >"$OUT/board.json"
"$KICAD_PY" "$ROOT/tools/kicad_place.py" "$OUT/charge-board.net.xml" "$OUT/board.json" \
  "$BOARD/charge-board.kicad_pcb" 2>&1 | grep -v 'wxApp'

# Connections are all open on purpose: routing has not started (plans/electronics.md, E3).
"$KICAD_CLI" pcb drc --format json --schematic-parity --severity-error \
  -o "$REPORTS/drc.json" "$BOARD/charge-board.kicad_pcb" >/dev/null 2>&1 || true
"$KICAD_CLI" pcb export step --grid-origin --subst-models --force --no-unspecified --no-dnp \
  -o "$OUT/charge-board.step" "$BOARD/charge-board.kicad_pcb" >/dev/null 2>&1
"$KICAD_CLI" pcb export glb --grid-origin --subst-models --force --include-tracks \
  -o "$OUT/charge-board.glb" "$BOARD/charge-board.kicad_pcb" >/dev/null 2>&1
echo "wrote build/kicad/charge-board.step and .glb"
