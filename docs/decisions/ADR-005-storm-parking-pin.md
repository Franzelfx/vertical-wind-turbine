# ADR-005: The generator cannot stop this rotor; a pin does

- Date: 2026-11-06
- Status: accepted 2026-11-06: manual pin chosen by the person, over an automatic brake

## Context
A wind turbine should have a way to stop. Shorting the generator is the usual one. Numbers from
`docs/sizing.md`: the small motor's torque is far below the rotor's in a storm, and all the rotor's
power would go into its windings. Stopping electrically needs a much lower resistance, then about 200 W
of heat: no motor of this size survives that, and a large one's cogging would stop the rotor starting.
Free-running, the rotor passes its assumed speed limit at about 24 m/s.

## Decision
- A **parking pin**: a 6 mm pin from below through a lug on the bracket, into a hole in the flange.
  It locks the rotor against the bracket. Use it before forecast storms and for any work on the turbine.
- The panel switch and resistor only **slow** the rotor, in light wind, so the pin can be fitted.
- Requirement MEC9 keeps the limit visible.

## Consequences
- **The system is not storm-proof unattended.** It depends on someone fitting the pin, and the 30 m/s
  survival figures assume it is fitted. In a storm with nobody home, the rotor free-runs: it might
  shed parts at height. Keep the fall zone clear, about the pier's height around it.
- Bench test B4 replaces the assumed speed limit. If you want this unattended, the next step is a
  centrifugal drum brake on the rod: a project of its own.
