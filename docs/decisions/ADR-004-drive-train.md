# ADR-004: Side-mounted, with a new drive train under the rotor

- Date: 2026-11-06
- Status: accepted 2026-11-06: side mount chosen by the person, over a top mount

## Context
The model is a decoration for a wall: it spins on two fixed M8 stubs, on 608 bearings in its end caps,
so **it has no output shaft**. A generator needs a new way to take torque out. Two ways to stand it on
an 80 x 80 mm pier:

| | Top-mounted, on the pier's end | Side-mounted, on the pier's face |
| --- | --- | --- |
| Wind access | clear on all sides | the pier shadows it a little |
| Rotor support | cantilever, 890 mm tall | carried at both ends |
| Shaft at 30 m/s, 144 N at 445 mm | about 64 N m: M8 fails many times over; needs about 25 mm of steel and a bearing tube | about 40 MPa in the M8 stub |
| Parts | a new machined column | one new printed bracket; the original on top |

## Decision
Side-mounted on the pier's -y face, with the model's own bracket on top. Below it, new parts:
- `drive_flange`: takes the place of the lower bearing, located in the seat, with three M4 through-bolts
  in the rotor's floor. The rotor is drilled through it, as a template.
- `drive_bracket`: two 608 bearings 48 mm apart, on the model's 140 mm reach, with a cage for the
  generator. An M8 stainless rod runs through it.
- `coupling`: printed TPU, to forgive misalignment.
- `generator_cover`: drains through its floor.

Generator: GM4108H-120T. Low cogging, 124 g, 53 rpm/V. A stepper would be the usual hobby choice, but
its detent torque would stop this rotor starting: the rotor makes only about 0.1 N m at 8 m/s.

## Consequences
- Print everything for outdoors in ASA, not the model's PLA, which softens in sun at about 55 degC.
- The rotor's tip passes 17 mm from the pier. The pier's own bend at 30 m/s does not change this,
  since rotor and pier move together.
- Weak spots: a printed bracket on a long reach; three M4 bolts in a printed floor; the motor's mounting
  pattern and the bell's fixing holes, which are assumptions until one is on the bench (B1). The drive
  from the rod into the bell through TPU is a sketch until then.
