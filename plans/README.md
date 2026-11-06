# Plans

Intent, not results. Current state: `tools/run-checks.sh` and the generated pages in `docs/`.

| Plan | Area |
| --- | --- |
| [requirements.md](requirements.md) | Numbered limits and where each stands (generated) |
| [mechanical.md](mechanical.md) | Rotor, drive train, enclosure, pier |
| [electronics.md](electronics.md) | Board, firmware |
| [bench.md](bench.md) | Physical tests that replace each assumption |

Rules:
- A plan lists intent and checklist items; it does not hold results. Results go into `docs/` (generated
  where possible) or into an ADR, and the plan item links to them.
- Tick an item in the same commit that completes it; update the plan's status line when a phase finishes.
- Legend in every plan: **[U]** your decision or action, **[C]** Claude does it, **[U+C]** together.
- Finished or superseded plans move to `archive/`.
