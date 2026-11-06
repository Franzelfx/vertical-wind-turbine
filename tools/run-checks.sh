#!/usr/bin/env bash
# Every check in one place. Non-zero exit on any violation. Rebuilds electronics and CAD first, so
# tests see current reports: about a minute and a half. Use `uv run pytest` alone for quick runs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORTS="$ROOT/build/reports"
mkdir -p "$REPORTS"
cd "$ROOT"

status=0
echo "== ruff check"
uv run --locked ruff check . || status=1
echo "== ruff format"
uv run --locked ruff format --check . || status=1
echo "== electronics"
tools/build-electronics.sh >"$REPORTS/electronics.log" 2>&1 || { tail -20 "$REPORTS/electronics.log"; status=1; }
echo "== CAD"
tools/build-cad.sh >"$REPORTS/cad.log" 2>&1 || { tail -20 "$REPORTS/cad.log"; status=1; }
echo "== pytest"
uv run --locked pytest -q --junitxml="$REPORTS/pytest.xml" || status=1
exit $status
