# ADR-009: The booklet is Typst, fed by the model

- Date: 2026-11-06
- Status: proposed; decided by Claude, the person asked for whichever format suits best; open for review

## Context
The person wants one PDF of the whole project for friends, technical and not. It needs a designed layout,
pictures, tables and the schematic. Its figures must not drift from the spec (ADR-002), but it reads as
a booklet, so the generated Markdown pages cannot simply be concatenated.

| Tried on paper | Why not |
| --- | --- |
| Pandoc from the Markdown pages | good for a report, poor for a designed page, and those pages are not written for everyone |
| LaTeX, installed here | works, but layout takes more effort and depends on a local TeX install |
| HTML through headless Chrome | depends on a local browser and its print behaviour |

## Decision
- **Typst**, through the `typst` Python package in the dev group, so `uv.lock` pins it. It embeds the
  schematic's PDF sheets directly.
- `report/booklet.typ` holds prose and layout. `src/vawt/io/report.py` writes `build/report/data.json`,
  the chart and smaller copies of the renders, then compiles. `uv run vawt pdf` runs it all.
- **Numbers in the prose come from `data.json`**: `tests/test_report.py` fails on a figure with a unit
  typed into the template. A few yardsticks for everyday comparisons sit in `src/vawt/spec.py`.
- Plain words first for everyone, with technical detail in marked boxes and reference pages.
- The PDF stays in `build/`, uncommitted, because it shows the licensed rotor (ADR-003).

## Consequences
- The font is Avenir Next, which comes with macOS. Elsewhere Typst falls back and warns, which the test
  treats as a failure.
- No test sees stale renders in the booklet, as with the renders themselves: run `tools/render.sh`
  first after visible changes.
- Prose can still go out of date where it describes a design in words. Change it with the design.
