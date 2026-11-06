# Vertical wind turbine

A small printed vertical-axis turbine on a 3 m, 80 x 80 mm timber pier, charging a 3S Li-ion pack
(the usual "12 V", 9.0-12.6 V) through its own electronics in a weatherproof box.

**Status:** digital design only. Enclosure and drive train are modelled and pass collision checks. The
schematic passes ERC, and the board is placed but not routed. No firmware. Nothing is built, and every
power figure is an estimate. Requirements: `plans/requirements.md`. Next steps: `plans/`.

**What to expect:** about 0.4 W on average at 3.5 m/s mean wind, about 4 kWh a year, and about 15-20 W at
best in a gale: this is a project to enjoy, not an energy source. A 20 W solar panel makes more. See
`docs/sizing.md`.

![The system on its pier, with its parts named](docs/images/render-site-labelled.png)

| | |
| --- | --- |
| ![The turbine side of the pier](docs/images/render-site.png) | ![The turbine from below](docs/images/render-turbine.png) |
| ![The upper bracket and top cap](docs/images/render-turbine-top.png) | ![From the side](docs/images/render-site-rear.png) |
| ![Enclosure on the pier](docs/images/render-enclosure.png) | ![Enclosure, from below](docs/images/render-enclosure-below.png) |
| ![Inside the enclosure](docs/images/render-enclosure-open.png) | ![Exploded enclosure](docs/images/render-enclosure-exploded.png) |
| ![Drive train with cover](docs/images/render-drive.png) | ![Drive train, cover off](docs/images/render-drive-open.png) |

The rotor is GeoJolt's "Ugrinsky Style wind Turbine" from MakerWorld, under its Standard Digital File
License: its files are not in this repository (ADR-003).

## Layout

```text
src/vawt/          spec.py: every number. system/: sizing and requirements. io/: docs, mesh import
cad/freecad/       The parts and assembly, as FreeCAD Python
cad/vendor/        The licensed rotor, not in git
electronics/       KiCad: charge-board/ with its schematic as code, lib/ with project parts
firmware/          ESP32-C3, not started
tools/             run-checks, build-cad, build-electronics, render
report/            The booklet's text and layout, as Typst
tests/             Requirements, CAD report, ERC and DRC, doc integrity
plans/             Intent: requirements, mechanical, electronics, bench tests
docs/              State: generated pages, decisions, images
datasheets/        Parts' datasheets
bench/runs/        Raw logs from physical tests
build/             Generated: STEP, STL, FCStd, reports. Not committed
```

## Use

Needs `uv`, FreeCAD 1.1, KiCad 10 and Blender, each in its default place or named by an environment
variable (`CLAUDE.md`). Put the 3MF in `cad/vendor/ugrinsky/`.

```sh
uv run vawt sizing          # the figures
tools/run-checks.sh         # everything, about 90 s
tools/render.sh             # the pictures, about 10 minutes (--samples 32 --width 800 for a draft)
uv run vawt pdf             # the booklet for friends: build/report/vertical-wind-turbine.pdf
```

Afterwards, `build/cad/wind-turbine.FCStd` opens in FreeCAD, `build/cad/` holds each part's STEP and
STL, and `electronics/charge-board/charge-board.kicad_pro` opens in KiCad. In FreeCAD, run
`cad/freecad/apply_colours.py` to colour the assembly. Change parts in the scripts, not in the
generated files (ADR-001).

## Safety

- Not storm-proof unattended: fit the parking pin before forecast storms, and keep the fall zone clear
  (ADR-005).
- A printed box does not contain a Li-ion fire (ADR-008).
- The rotor's underside is 2 m up and the tips move fast. Fit the pin before touching it.
