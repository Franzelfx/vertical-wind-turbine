# ADR-008: A printed ASA enclosure on the pier's shaded side

- Date: 2026-11-06
- Status: proposed; decided by Claude; open for review

## Context
The box holds a Li-ion pack outdoors for years, at chest height on a timber post. It has to survive rain,
sun and condensation, and it fits a 256 mm print bed.

## Decision
- **Tub, lid and a separate rain hood**, printed in ASA in pale grey: UV-stable, reflects sun.
- **Gasket:** 3 mm EPDM cord in a groove in the rim, 27 % squeeze. Six M4 screws in heat-set inserts,
  outside the seal.
- **Nothing opens upwards.** Two M16 glands, an M12 pressure vent and an M12 sealed brake switch, all
  on the bottom face. The vent stops pressure swings pulling damp air past the gasket.
- **Eight millimetre standoffs from the wood**, so the post can dry behind the box. Four M6 coach screws
  on the 60 mm spacing, all outside the sealed volume. Ears reach past the rim so a socket fits.
- **Hood with a 6 mm air gap**, shading the lid and shedding rain past the rim.
- **Inside:** board on top, standoffs integral. Pack low in a folded galvanised steel pan with a strap.
  It stays clear of the board, so heat goes up away from it. Brake resistor on the floor.
- **Position:** on the +y face at 1350 mm, **which should face north**, away from sun, and on the side
  away from the rotor, so service is not under it.

## Consequences
- ASA is not flame-retardant. **A printed box will not contain a Li-ion fire.** The steel pan and the
  BMS reduce the risk, they do not remove it. Mount it on nothing that burns fast, away from buildings.
  A timber post is itself combustible; a steel plate behind the box is a cheap improvement. Use a bought
  pack with a real BMS and cell-level fusing.
- Printed walls leak unless tuned: at least 4 perimeters, then seal test B6. Printed threads are not
  used anywhere for sealing, because the glands have nuts inside.
- The 25 W brake resistor has no heat sink beyond the box, which is why the brake is for short use only.
- Width is 148 mm on an 80 mm pier: the body overhangs, and only the screws need to land on the post.
