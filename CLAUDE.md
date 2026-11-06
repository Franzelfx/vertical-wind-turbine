# CLAUDE.md

Small vertical-axis wind turbine charging a 3S Li-ion pack, on an 80 x 80 mm, 3 m timber pier. Rotor: a
licensed printed model, side-mounted (ADR-003, ADR-004), with a new drive train to a gimbal-motor
generator. Charger BQ25798 with an ESP32-C3 (ADR-007). A self-powered relay protects it (ADR-006). Printed
ASA enclosure (ADR-008). Not storm-proof unattended (ADR-005). Nothing has been built or tested yet.
How this repository works: `PROJECT-PLAYBOOK.md` (it describes another project; its method applies).

## Conventions
- All shared values live in `src/vawt/spec.py`. Never hard-code them elsewhere; add to the spec first. It
  stays standard-library only, because FreeCAD's Python imports it. Unmeasured values carry the literal
  word `ASSUMPTION` and a bench test in `plans/bench.md`.
- Coordinates: z up, origin on the pier axis at ground. Turbine on -y, enclosure on +y. Board x is
  mirrored in the box (ADR-007).
- Generated, never edit by hand: `docs/sizing.md`, `docs/assumptions.md`, `docs/printing.md`, `docs/bom.md`, `plans/requirements.md`, the
  guard-rail block below, `electronics/charge-board/*.kicad_sch`, `electronics/charge-board/charge-board.kicad_pcb`
  (until E3 starts hand layout), everything in `build/`. Change the source, run the command, commit both.
- Generated output (`build/`) is never committed. It holds the licensed meshes too: never commit those.
- Non-obvious design choices get an ADR in `docs/decisions/` (copy `ADR-000-template.md`), in the same
  commit as the change. Mark AI decisions as such.
- `plans/` holds intent; `docs/` holds only what code and tools produce, plus ADRs.
- Tick a plan item in the same commit that completes it. `[U]` items are the person's: reviews, purchases,
  physical tests. Do not do them or tick them.
- Backticked paths in Markdown must exist (`tests/test_docs.py`), except those under `build/`.

## Commands
- Checks: `tools/run-checks.sh`, about 90 s: lint, format, electronics, CAD, tests. Must pass before commit.
  `uv run pytest` alone reuses the last build; a stale CAD report fails by fingerprint.
- `uv run vawt` lists commands. `uv run vawt sizing`: the figures. `uv run vawt docs`: after any change to
  the spec, a requirement or a plan's status line.
- `tools/build-cad.sh`, about 10 s: parts, assembly, report. Run `tools/build-electronics.sh` first (60 s)
  if the board changed, since CAD reads its STEP.
- `tools/bom.py`, needs network, seconds: refreshes the dated stock snapshot `docs/bom.md`. Run by hand after
  changing parts; `tests/test_electronics.py` fails when a part is missing from it.
- `tools/render.sh [--only NAME] [--samples N] [--width W]`, a few minutes: writes `docs/images/render-*.png`.
  Run by hand after visible changes; no test sees stale PNGs.

## Tools
- `freecadcmd` exits 0 when a script raises: `tools/build-cad.sh` reads the log instead. A placed mesh's
  `BoundBox` is the rotated local box and far too large: use its points. Fillet with the same object's
  edges, not an equal copy's.
- FreeCAD's GUI does not run scripts under Qt's offscreen platform: `freecadcmd` it is, no colours.
- `kicad-cli` prints harmless Fontconfig and NSCocoaError lines. Go by its exit code and reports.
- KiCad's Python is 3.9 and cannot import `vawt`: `tools/kicad_place.py` gets `build/kicad/board.json`.
- MakerWorld answers 403 to automated requests: the 3MF comes from a person (ADR-003).

## Machine notes (macOS)
- `uv`, `kicad-cli` and `ffmpeg` are on `PATH`. FreeCAD and Blender are apps: `FREECADCMD`, `KICAD_CLI`,
  `KICAD_PY`, `BLENDER` and `KICAD_SYMBOL_DIR` override their paths.
- KiCad and Blender MCP servers failed to connect on 2026-11-06; nothing here needs them.

## Guard rails
Holding on paper, not measured. Evidence in brackets: M measured from a file, S a source, E an estimate.
<!-- vawt:guard-rails:start -->
- SYS1: Charge voltage: 3S Li-ion, the `12 V` pack in the brief: at most 12.6 V; now 12.6 V (holds on [S]).
- SYS2: Mean wind fills the pack in: at most 14 days; now 7.349 days (holds on [E]).
- SYS3: Pack drain with the rotor standing: charger, regulator, MCU, BMS: at most 1 mW; now 0.5457 mW (holds on [E]).
- SYS4: Wind at which charging begins: at most 4 m/s; now 2.8 m/s (holds on [E]).
- SYS5: Wind at which the rotor starts against cogging and drag: at most 3 m/s; now 2.129 m/s (holds on [E]).
- ELE1: Relay trips below the charger's overvoltage stop: at most 26 V; now 22.5 V (holds on [E]).
- ELE2: Open-circuit bus at survival wind, within the 100 V parts: at most 100 V; now 70.8 V (holds on [E]).
- ELE3: Relay series resistors at survival wind: at most 9 W; now 5.762 W (holds on [E]).
- ELE4: Generator current at peak power, within the motor's rating: at most 1.5 A; now 1.031 A (holds on [E]).
- ELE5: Generator copper loss at peak power: at most 12 W; now 11.7 W (holds on [E]).
- ELE6: Charger input current at peak power: at most 3.3 A; now 1.031 A (holds on [S]).
- MEC1: Rotor tip to pier face: at least 15 mm; now 17.5 mm (holds on [M]).
- MEC2: Rotor underside above ground, out of reach: at least 2000 mm; now 2010 mm (holds on [M]).
- MEC3: Longest printed enclosure part on the print bed: at most 256 mm; now 244 mm (holds on [M]).
- MEC4: Enclosure screws stay on the pier's face: at most 80 mm; now 72.5 mm (holds on [M]).
- MEC5: Pier utilisation at survival wind, EN 1995 style: at most 1; now 0.6853 (holds on [E]).
- MEC6: Swing at the rotor when imbalance sits on the pier's first mode: at most 5 mm; now 1.26 mm (holds on [E]).
- MEC7: Bracket arm bending at survival wind, ASA with layer knock-down: at most 10 MPa; now 2.415 MPa (holds on [E]).
- MEC8: M8 stub bending at survival wind, A2-70: at most 200 MPa; now 40.3 MPa (holds on [E]).
- MEC9: Wind at which a free-running rotor reaches its speed limit: lock it above: at least 20 m/s; now 24.05 m/s (holds on [E]).
- ENC1: Gasket squeeze, lower bound: at least 20 %; now 26.67 % (holds on [M]).
- ENC2: Gasket squeeze, upper bound: at most 35 %; now 26.67 % (holds on [M]).
- ENC3: Tallest board part to the lid's inner face: at least 5 mm; now 22.9 mm (holds on [M]).
<!-- vawt:guard-rails:end -->
- Lithium: never charge below 0 degC (TS pin, hardware). Pack with a real BMS, in the steel pan.
- No one works on the turbine with the rotor free: fit the parking pin first (ADR-005).
