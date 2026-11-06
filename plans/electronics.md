# Plan: Electronics

Goal: a routed, fabricated, working charge board, and firmware that tracks the rotor's best point.

**Status (2026-11-06):** schematic generated, ERC clean. Board has a first-pass placement that passes DRC,
with all connections still open. No firmware. Next: E2.

Rules for every step:
- Each pin names a net or NC: `electronics/charge-board/schematic/build.py` is the source.
- Done means: `tools/run-checks.sh` passes and the item is ticked here in the same commit.

Legend: **[U]** your decision or action, **[C]** Claude does it, **[U+C]** together.

---

## Phase E0: Decisions
- [ ] [U] Review ADR-006 (relay) and ADR-007 (charger and MCU)
- [x] [U] "12 V Li-ion" means 3S, not 4S LiFePO4 (confirmed 2026-11-06)
- [ ] [U] Decide on the pack: buy, then measure it against the tray

## Phase E1: Schematic
- [x] [C] Bridge, relay, charger, controller as code
- [x] [C] First-pass board from the netlist; 3D export into CAD (`tools/kicad_place.py`)
- [ ] [U] Review the schematic: `docs/images/charge-board-schematic.pdf`

## Phase E2: Parts
- [ ] [C] Check every part against its datasheet, starting with the inductors and the AO3400's gate limit
- [ ] [C] LCSC numbers and stock; `tools/` from `battery-swap-drone` can be reused

## Phase E3: Layout
- [ ] [U+C] Real placement: the buck-boost loop first, per the BQ25798 datasheet 8.4
- [ ] [C] Keep 100 V nets apart from the rest, and copper under the inductor out
- [ ] [C] Route, then DRC with no open connections
- [ ] [U] Review, then order

## Phase E4: Firmware (`firmware/`)
- [ ] [C] Charger setup over I2C: watchdog, ADC, charge current, input limit
- [ ] [C] Deep sleep with wake on the charger's INT
- [ ] [C] Hill-climbing on VINDPM, from the charger's ADC
- [ ] [C] Relay release once the bus falls
- [ ] [C] Wi-Fi telemetry

## Phase E5: Bring-up
- [ ] [U] Current-limited power on the bench. Charge a pack from a lab supply (B2)
- [ ] [U] Prove the relay trips with no battery connected (B2)
