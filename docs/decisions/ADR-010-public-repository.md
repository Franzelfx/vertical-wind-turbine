# ADR-010: How the public repository presents itself

- Date: 2026-11-07
- Status: proposed; decided by Claude, asked to set the repository up for GitHub; open for review

## Context
The repository is public on GitHub (ADR-003). Its README showed all 11 full-size renders, about 43 MB
through Git LFS, and LFS bandwidth is metered on the owner's account for every viewer. A clean clone also
has no CAD or electronics reports, no licensed rotor and possibly not the booklet's font.

## Decision
- **Light copies for the page:** `tools/web_images.sh` writes small JPEGs to `docs/images/web/`, which
  `.gitattributes` keeps out of LFS. Each links to its full render.
- **CI runs what a clean clone can run:** lint, the sizing model, requirements and docs. CAD, electronics
  and the booklet stay with `tools/run-checks.sh` on a workstation, so a green badge does not cover them.
- **The README's figures are generated** between markers by `uv run vawt docs`, like the guard rails.
- **Generated files are marked** `linguist-generated`, so GitHub collapses them in diffs.
- **No licence file yet.** That choice is the person's, and it could not cover the rotor or the datasheets.

## Consequences
- Without a licence, the default applies: others may read this repository, not reuse it.
- Re-rendering changes the JPEGs, and each change adds to git history: under 1 MB a time.
- `tools/run-checks.sh` rewrites `charge-board.kicad_pcb` and the schematic PDF with fresh UUIDs even when
  nothing changed. Discard that churn unless the board really changed.
