# Plan: Mechanical

Goal: rotor, drive train and enclosure on the pier, printed and assembled, surviving a year outdoors.

**Status (2026-11-06):** digital design complete and checked for collisions. Nothing printed. Next: M0.

Rules for every step:
- Values go into `src/vawt/spec.py` first; each geometry step adds a test in `tests/test_cad.py`.
- Done means: `tools/run-checks.sh` passes and the item is ticked here in the same commit.

Legend: **[U]** your decision or action, **[C]** Claude does it, **[U+C]** together.

---

## Phase M0: Decisions
- [x] [U] ADR-004: side mount on the pier, new drive train (chosen 2026-11-06)
- [x] [U] ADR-005: storm parking by hand, fall zone kept clear (chosen 2026-11-06)
- [ ] [U] Check the 3MF is the model you meant and read its licence (ADR-003)
- [ ] [U] Pick the site, and which face points north

## Phase M1: Digital design
- [x] [C] Import the rotor, measure hub, twist and bracket from the meshes
- [x] [C] Drive flange, bracket, motor plate, coupling and cover in `cad/freecad/drivetrain.py`
- [x] [C] Tub, lid, hood and gasket in `cad/freecad/enclosure.py`
- [x] [C] Assembly on the pier, collision checks, renders
- [ ] [C] Add the print orientation of each part, with an overhang check

## Phase M2: First prints
Cheap, early, and before the full rotor: the 13.5 h sections come after these.
- [ ] [U] Print a section of the enclosure's rim and test gasket squeeze (B6)
- [ ] [U] Print the drive bracket, fit bearings, motor and rod (B1)
- [ ] [U+C] Feed the real motor pattern and sizes back into the spec

## Phase M3: Rotor
- [ ] [U] Print the rotor in ASA
- [ ] [U] Spin and balance it (B4): gate before it goes up the pier
- [ ] [U] Drill through the flange, bolt up, fit the top bearing

## Phase M4: Site
- [ ] [U] Set the ground socket and pier; mount brackets
- [ ] [U] Log the wind for a month (B5)
