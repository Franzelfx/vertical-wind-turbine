# Hardware

> Written by hand from `src/vawt/spec.py` and the schematic; the netlist in `build/kicad/` is the full
> electronic part list. Only the board's parts have prices and stock so far: `docs/bom.md`.

## Print (ASA unless noted)

| Part | File after `tools/build-cad.sh` | Notes |
| --- | --- | --- |
| Rotor: bottom, 3 x middle, top | your 3MF | ASA instead of PLA. About 1.7 kg, 13.5 h per section |
| Upper bracket | your 3MF | The model's own |
| This project's parts | see `docs/printing.md` | Orientation and supports for each |

## Mechanical

| Item | Qty | Use |
| --- | --- | --- |
| 80 x 80 mm timber post, 3 m, plus ground socket | 1 | Pier |
| 608 bearing, 22 x 7 mm, sealed (2RS) | 3 | Two on the rod, one in the top cap |
| M8 threaded rod, A2 stainless, nuts, a locking nut | 1 set | Drive rod and upper stub |
| M8 coach screw, stainless | 8 | Both brackets into the pier |
| M6 x 70 coach screw, stainless | 4 | Enclosure into the pier |
| M4 x 16 screws with locking nuts | 3 | Flange through the rotor's floor |
| M4 x 12 screws, M4 heat-set inserts | 6 | Lid |
| Printed standoffs (`docs/printing.md`) | 4 | Between the tub and the wood |
| M3 x 5 heat-set inserts, M3 screws | 4 | Board |
| 6 mm stainless pin with a lanyard | 1 | Parking pin, ADR-005 |
| 3 mm EPDM cord, about 750 mm | 1 | Lid gasket |
| Conduit M16, clips | 1.5 m, 5 | Generator cable on the pier |

## Electrical

| Item | Qty | Use |
| --- | --- | --- |
| GM4108H-120T gimbal motor | 1 | Generator |
| 3S2P 18650 pack with BMS, 7 Ah, with a 10k NTC | 1 | The battery. Check the size against the tray |
| Charge board, `electronics/charge-board/`, parts in `docs/bom.md` | 1 | Not routed yet |
| M16 cable gland, IP68 | 2 | Generator, load |
| M12 pressure vent | 1 | Bottom face |
| M12 sealed toggle switch | 1 | Brake |
| 4.7 ohm 25 W aluminium-clad resistor | 1 | Brake |
| Galvanised steel pan, folded, strap | 1 | Pack tray, ADR-008 |
