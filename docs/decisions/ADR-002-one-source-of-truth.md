# ADR-002: Every number has one home, and tests watch the tool boundaries

- Date: 2026-11-06
- Status: proposed; decided by Claude; open for review

## Context
The same dimensions are needed by sizing (Python 3.12), CAD (FreeCAD's Python 3.11) and KiCad (its
Python 3.9). Copies drift; the playbook's section 10 lists what drifted in `battery-swap-drone`.

## Decision
- `src/vawt/spec.py` holds every shared number. Standard library only, so FreeCAD can import it, which
  `tests/test_architecture.py` enforces. KiCad's Python gets a JSON exchange file from it.
- Requirements live in `src/vawt/system/requirements.py` and generate `plans/requirements.md`.
- Results go in generated pages. `tests/test_docs.py` fails on any drift, a missing index entry, a
  stale path or a missing ADR, the gaps the playbook found in the earlier project.
- `tests/test_cad.py` reads FreeCAD's report, with a fingerprint so a stale report cannot pass, and
  proves the collision check can fail with a seeded overlap.

## Consequences
`tools/run-checks.sh` is the one gate. It takes about 90 seconds because it rebuilds CAD and the board.
The repository is local, with no remote, by the person's choice on 2026-11-06, so there is no CI yet.
