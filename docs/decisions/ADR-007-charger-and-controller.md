# ADR-007: BQ25798 charger, tracked by an ESP32-C3

- Date: 2026-11-06
- Status: proposed; decided by Claude; open for review. 3S Li-ion confirmed by the person 2026-11-06

## Context
A low-speed generator gives 4-20 V, either side of a 3S pack (9.0-12.6 V). So the charger must buck and
boost. "12 V Li-ion" is read as 3S: 10.8 V nominal, 12.6 V full. A 4S LiFePO4 pack also passes as "12 V"
but charges differently, and this project does not cover it.

## Decision
- **BQ25798**: 3.6-24 V input, 1-4 cells, buck-boost, integrated FETs, already used in
  `battery-swap-drone`, whose symbol and footprint are reused. PROG sets 3S at 750 kHz (Table 7-1).
- **Its built-in MPPT is not used.** It samples open-circuit voltage for solar panels. A rotor has no
  fixed curve: its speed collapses during a sample. The ESP32-C3 hill-climbs by writing VINDPM instead,
  from the charger's ADC. Without firmware the charger still charges, at its 3.6 V default input limit,
  which keeps the bus low but makes little power.
- **ESP32-C3-WROOM-02**: Wi-Fi for telemetry, deep sleep at standstill. The charger's INT wakes it on
  IO3, because C3 deep sleep only wakes on GPIO 0-5. Supply: AP63203, 22 uA.
- **Li-ion below freezing**: an NTC on the pack, on the charger's TS pin, stops charging below 0 degC
  in hardware. This is a safety function, not a firmware feature.

## Consequences
- Firmware is real work and is not written yet (`plans/electronics.md`, E4).
- Seen from the front of the box, the board's x axis is mirrored, since it faces +y. So its GENERATOR
  terminal is on the box's +x side, which is where the gland and the pier's cable run are.
- 0.4 mm pitch QFN: needs a fab with 0.1 mm gaps. `charge-board.kicad_dru` allows exactly that part.
