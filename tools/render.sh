#!/usr/bin/env bash
# PNG renders in docs/images/: rebuilds CAD, then renders each view in Blender (Cycles).
# Other arguments go to the Blender script, e.g. tools/render.sh --only site --samples 32
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
"$ROOT/tools/build-cad.sh" >/dev/null
"$BLENDER" -b --factory-startup -P "$ROOT/tools/render_blender.py" -- "$@" \
  | grep -E "^wrote|Error|Traceback" || true
cd "$ROOT" && uv run python tools/label_render.py
