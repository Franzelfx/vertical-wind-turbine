# ADR-001: FreeCAD, KiCad and Blender, driven by scripts

- Date: 2026-11-06
- Status: proposed; decided by Claude within the brief ("freecad and kicad"); open for review

## Context
The brief names FreeCAD and KiCad. `battery-swap-drone` and `gpu-heat-nodes` model parts in build123d
and only use FreeCAD for the assembly, so following them exactly would make FreeCAD a viewer.

## Decision
- **CAD:** FreeCAD 1.1 is the kernel, driven by Python in `cad/freecad/` through `freecadcmd`. No
  build123d. `tools/build-cad.sh` writes the assembly as a real `.FCStd`, plus STEP and STL per part.
- **Electronics:** KiCad 10. The schematic is code (`electronics/charge-board/schematic/build.py`,
  with `tools/schgen.py` from `battery-swap-drone`); placement is a script under KiCad's Python.
- **Renders:** Blender Cycles, headless, as in both earlier projects.
- **Sizing:** plain Python, standard library only, in `src/vawt/`.

Tried on this machine first (playbook, section 4): `freecadcmd` builds and saves documents; `kicad-cli`
runs ERC, DRC and 3D export; KiCad's Python loads `pcbnew`; Blender renders headless.

## Consequences
- The `.FCStd` is generated. Hand edits are lost on the next build, so **parts change in the scripts**.
  Its objects are solids, not a parametric feature tree: if you want to edit in FreeCAD's GUI, say so
  and the tree can be built from Part features instead.
- `freecadcmd` cannot store colours, and FreeCAD's GUI does not run scripts under Qt's offscreen
  platform. `cad/freecad/apply_colours.py` colours the file from inside the GUI; it has not been run,
  because that needs a person at the app.
- The KiCad and Blender MCP servers failed to connect on 2026-11-06. Nothing here needs them.
