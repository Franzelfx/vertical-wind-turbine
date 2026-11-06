#!/usr/bin/env bash
# Light JPEG copies of the renders for the README, in docs/images/web/. They stay out of Git LFS so a
# page view costs no LFS bandwidth (ADR-010). tools/render.sh runs this; needs ImageMagick's `magick`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MAGICK="${MAGICK:-magick}"
OUT="$ROOT/docs/images/web"
mkdir -p "$OUT"
for source in "$ROOT"/docs/images/render-*.png; do
  name="$(basename "$source" .png)"
  # The overview's labels must stay readable, so it keeps more pixels
  [ "$name" = "render-site-labelled" ] && width=1120 || width=720
  "$MAGICK" "$source" -resize "${width}x" -strip -sampling-factor 4:2:0 -quality 78 "$OUT/$name.jpg"
done
du -sh "$OUT"
