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

## Update: parts checked against datasheets and stock (2026-11-06)
- BQ25798: symbol pins match Table 5-1 (`tests/test_electronics.py`). Section 8.2.2.2: 750 kHz only works
  with a 2.2 uH inductor, which the board has; saturation at least 2 A. PROG 13.7k is Table 7-1.
- AP63203: Table 2 recommends 3.9 uH at 3.3 V. Section 10 allows 2.2-10 uH. The only 3.9 uH parts
  found are larger or barely stocked, so the board keeps 4.7 uH in the smaller package. Ripple is about
  0.47 A at 12.6 V in. **Decided by Claude; watch the output at bring-up (B2).**
- Replaced: the 3 W 12 V zener with `1SMB5927B`, since `3SMBJ5927B` has no stock. Terminal blocks are KF128
  at 5.08 mm, since the cheaper KF301 is 5.0 mm and would not fit the footprint.
- Not at JLCPCB, to be hand-fitted: the 1.8k 3 W resistors and the mini blade fuse holders. **The KiCad
  fuse footprint solders the blade itself in, so a blown fuse cannot be swapped. Replace it in E3.**
- Not yet read: the datasheets for the relay, Schottky diodes, zeners and MOSFETs (E2).
