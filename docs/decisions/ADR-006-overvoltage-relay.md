# ADR-006: A relay powered by the overvoltage itself isolates the charger

- Date: 2026-11-06
- Status: proposed; decided by Claude; open for review

## Context
When the pack is full the charger stops, the rotor free-runs, and the bus rises: it passes the charger's
24 V at about 10 m/s and reaches about 71 V at 30 m/s. The charger's absolute limit is 30 V. Protection
must work with a dead pack, a sleeping MCU and a crashed firmware.

| Tried on paper | Why not |
| --- | --- |
| Shunt the bus with a MOSFET | puts all the rotor's power into the small motor (ADR-005) |
| Dump load | 100 W+ of resistor at 70 V, in a sealed printed box |
| Series P-MOSFET | a 100 V P-channel needs more gate than a 3.6 V cut-in bus can give |
| Surge stopper IC | common parts stop at 60 V, with little margin at 71 V |
| A higher-voltage charger | parts with 80 V inputs cost far more and need external FETs |
| A higher-KV generator | keeps the bus low, but then it cannot reach 3.6 V at low wind |

## Decision
A normally closed relay (K1) between the bridge and the charger. Its coil hangs on the raw bus through
series resistors, so it picks up by itself at about 22.5 V, below the charger's 26 V stop. With the
generator then open-circuit, nothing heats up and the rotor runs free, as the original model does. A
12 V zener holds the coil at its rating at higher voltage. Bridge, relay driver and resistors are rated
for the full open-circuit voltage: 100 V.

Once picked up, the relay holds down to a very low voltage. So the MCU releases it: when it sees the bus
has fallen, it pulses `RELAY_RELEASE`. If that firmware fails, the relay just stays open until the rotor
almost stops, which is safe.

## Consequences
- About 2-3 % of the power goes to the coil path while running. Accepted for protection needing no battery.
- Weak spots: pick-up voltage has a spread (B2); relay contacts see a small DC load at low voltage
  and at about 1 A in the worst case; and the resistors reach 5.8 W at 30 m/s, for which there are three
  in parallel. The symbol's drawing shows pin 4 as normally closed: check with a meter before fitting.
