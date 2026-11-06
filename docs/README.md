# Docs

What exists now, each page naming its source. Intent lives in `plans/`.

| Page | Contents | Source |
| --- | --- | --- |
| [sizing.md](sizing.md) | Power, yield, overvoltage, stopping, structure, vibration | generated, `uv run vawt docs` |
| [assumptions.md](assumptions.md) | Every number nobody has measured | generated, `uv run vawt docs` |
| [hardware.md](hardware.md) | What to buy and print | by hand |
| [images/](images/) | Renders and the schematic PDF | `tools/render.sh`, `tools/build-electronics.sh` |

## Decisions

| Record | Decision |
| --- | --- |
| [ADR-001-tools.md](decisions/ADR-001-tools.md) | FreeCAD, KiCad and Blender, driven by scripts |
| [ADR-002-one-source-of-truth.md](decisions/ADR-002-one-source-of-truth.md) | Every number has one home |
| [ADR-003-rotor-licence.md](decisions/ADR-003-rotor-licence.md) | The rotor's meshes stay out of git |
| [ADR-004-drive-train.md](decisions/ADR-004-drive-train.md) | Side-mounted, with a new drive train |
| [ADR-005-storm-parking-pin.md](decisions/ADR-005-storm-parking-pin.md) | The generator cannot stop the rotor; a pin does |
| [ADR-006-overvoltage-relay.md](decisions/ADR-006-overvoltage-relay.md) | A self-powered relay isolates the charger |
| [ADR-007-charger-and-controller.md](decisions/ADR-007-charger-and-controller.md) | BQ25798, tracked by an ESP32-C3 |
| [ADR-008-enclosure.md](decisions/ADR-008-enclosure.md) | A printed ASA enclosure on the shaded side |
