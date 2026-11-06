# Plan: Bench

Goal: replace each `ASSUMPTION` in `src/vawt/spec.py` with a measurement, cheapest and riskiest first.

**Status (2026-11-06):** none run. Next: B1, since the generator costs little and everything rests on it.

Rules for every step:
- Change the spec, rerun `uv run vawt docs`, and if a limit breaks, that is the result: do not hide it.
- Raw logs go in `bench/runs/`.

Legend: **[U]** your decision or action, **[C]** Claude does it, **[U+C]** together.

---

- [ ] [U] **B1 Generator.** Meter across two phases: resistance. Spin with a drill and a tacho: rpm/V.
      Torque to turn it by hand with a spring scale: cogging and drag. Measure holes, bell and shaft;
      check that the hollow shaft turns with the bell.
- [ ] [U] **B2 Electronics.** Charger efficiency at 1 W and 10 W. Relay: continuity on pin 4 at rest,
      pick-up voltage on a lab supply. Copper temperature at 1 A, in the air. BMS's own drain.
- [ ] [U+C] **B3 Rotor curve.** One rotor on the drive train, in a car at a known speed on a calm day
      or by a large fan, with a resistor box: torque against speed at several winds. This replaces
      Cp, the best tip speed ratio and the no-load ratio. Biggest effect on every figure.
- [ ] [U] **B4 Spin and balance.** Test rig outdoors, behind cover. Drill-driven up to the rated speed
      in steps, watching for cracks. Balance by adding weight until it runs still. Sets `max_rpm` and
      the imbalance. Gate: nothing goes up the pier before this passes.
- [ ] [U] **B5 Site.** Log wind for a month beside the pier. Pluck the fitted pier for its frequency and
      damping: sets `mean_wind_m_s` and `damping_q`.
- [ ] [U] **B6 Seal.** Printed rim piece with cord: check squeeze. Whole box: 30 min under a hose, paper
      inside. Leave out a winter night, check for condensation.
