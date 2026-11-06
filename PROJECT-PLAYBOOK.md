# Project playbook

How the battery-swap drone repository is built, and how to set up a new project the same way.
Paths and examples refer to that repository (`battery-swap-drone`). Section 11 applies only to
hardware built with CAD and EDA tools; the rest applies to most projects.

## How far this has been proven

The drone is a 2S quadcopter with a swappable battery pack: three printed parts, a 6-layer frame
PCB with 500+ parts, and firmware configuration. A person and Claude built the digital design in
36 commits over about 45 hours (2026-10-21 to 2026-10-23).

| Size of the work | Count |
| --- | --- |
| Decision records | 19 |
| Plans | 5 |
| Test files / test functions | 22 / 135 |
| Python in the package layers and board scripts | ~9,000 lines |

**The method has only been proven on the digital design.** Nothing has been printed, ordered or
flown yet. The PCB still has 176 connections that the router could not make. Masses and currents
are model estimates (±25 % until thrust-stand data exists). So this playbook shows that the method
keeps a large design consistent and moving fast. It does not yet show that the design is right.

## 1. The rules in short

1. **Every number has one home.** All shared values live in one specification layer. Everything
   else derives from it.
2. **Generate artifacts instead of drawing them.** That includes artifacts normally made by hand:
   schematics, board outlines, placement, documentation tables.
3. **A test fails when any copy drifts.** Whatever crosses a tool boundary gets a test that
   compares both sides.
4. **Requirements are tests.** A weight ceiling or a voltage limit is an assertion, not a sentence
   in a document.
5. **Keep intent, state and reasons apart.** Plans hold what we intend, generated docs hold what
   exists, decision records hold why.
6. **Done means checks pass and the plan item is ticked in the same commit.**
7. **Verify the tools as well as the design.** Compare solvers with theory, and feed checks a known
   failure to show they can fail.
8. **Label every assumption** and name the physical test that will replace it.
9. **State who does what.** Each task is marked as the person's, the AI's, or shared.

## 2. Repository layout

```text
CLAUDE.md          Conventions, commands and guard rails for the AI (short, ~100 lines)
README.md          What the thing is and its status, with renders
plans/             Intent: requirements, phased checklists, open work
  README.md        Plan index and the rules for plans
  archive/         Finished or superseded plans
docs/              State: what the code and tools produce; each page names its source
  README.md        Page index: contents and source of each page
  decisions/       ADR-000-template.md, ADR-001...
  images/          Rendered images
mechanical/        Main Python package (src layout), tests, pyproject, lockfile
electronics/       KiCad project, schematic and layout generators, project part library
firmware/          Configuration, checked against the schematic by tests
tools/             Shell and Python entry points: checks, exports, renders
build/, export/, fab/   Generated output, never committed
```

The split that matters most is **`plans/` against `docs/`**. A plan never holds results. It links
to the doc or decision record that does.

## 3. One source of truth

**Layered package.** Imports only point downwards, so low layers stay fast and free of heavy
dependencies:

```text
spec        pure data: frozen dataclasses, components, materials, process limits, derived values
system      calculations without CAD: sizing, placement, centre of gravity
interfaces  how parts meet: swap contacts, clamps, pockets
features    reusable geometry
parts       one module per part, plus a registry that export and checks iterate over
assembly    parts combined: interference, mass
analysis    FEM, impedance, power distribution
io          KiCad, exports, generated docs, reports
cli.py      one entry point: `uv run drone <command>`
```

A test enforces the boundary: `test_sizing_has_no_cad_dependency` imports the system layer in a
fresh process and asserts that `build123d` was not loaded.

**How to write the specification (`spec/`):**
- Use frozen dataclasses with units in the docstring and a comment for any non-obvious value.
- Add to the spec first, then to the part. Never hard-code a shared dimension anywhere else.
- Mark placeholder values with the literal word `ASSUMPTION`, so they can be found by a search.
  `plans/mechanical.md` Phase 7 then replaces each one with a measured value.
- Fix one coordinate system and write it down (here: x forward, y left, z up, origin at the frame
  centre on the PCB bottom). Also record how it maps onto each tool's coordinates.
- Use a registry when several consumers iterate over the same things. `parts/registry.py` holds
  each part's build function, material and print orientation, and export, assembly and the
  printability checks all read it.

**Crossing tool boundaries.** When another tool or Python version can't import the package, write
a generated exchange file and test it. `tools/pcb_mechanics.py` writes `layout/mechanics.json` for
KiCad's Python, and `test_layout_constraints_in_sync` regenerates it and compares.

**Results flow back too.** Measured or modelled values update the budget, and a test forces the
update. The printed-part masses come from the CAD models, and the copper fill measured on the
routed board feeds the mass budget (`test_copper_fill_in_spec`). The power simulation takes its
loads from the sizing code, so it follows the mass budget automatically.

## 4. Generate everything you can

| Artifact | Generator | Guard |
| --- | --- | --- |
| Board outline and holes | `drone pcb-outline` | `test_kicad_edge_cuts_in_sync_with_model` |
| Interface footprints | `drone pcb-footprints` | `test_swap_contacts_file_in_sync` |
| Schematic | `schematic/build.py` + `tools/schgen.py` | ERC; an unassigned pin is an error |
| Placement, zones, routing | `layout/place.py`, `zones.py`, `critical.py`, `route.py`, `finish.py` | DRC with schematic parity |
| Power budget page | `drone docs` | `test_generated_page_in_sync` |
| Structure, power distribution and impedance pages | `drone fem`, `drone pdn`, `drone impedance` | staleness tests (section 5) |
| BOM | `tools/bom.py` | dated snapshot, committed |
| README images | `tools/render-readme.sh` | run by hand when the geometry changes visibly |

**Rules for generators:**
- **Deterministic output.** The schematic generator derives UUIDs from part references, so a rerun
  gives a clean diff. Without this, reviewing generated files is impossible.
- **Strict input.** Each pin must name a net or be explicitly `NC`. Silence is an error.
- **Rerunnable steps.** Each layout script replaces only the items it owns, and the order is
  documented, so a change upstream means a rerun rather than a redraw.
- **Report what could not be done.** The router makes 538 of 714 open connections and lists the
  other 176 in `docs/routing.md`. A generator that hides its gaps is worse than none.
- **Decide what is committed.** Generated files that are themselves the project (`.kicad_sch`,
  `.kicad_pcb`, generated docs) are committed and never edited by hand. Derived outputs (Gerbers,
  STL, STEP exports) are not committed.
- **Say where hand work goes.** Manual edits are lost when the owning script reruns, so ADR-019
  defines where the hand-finished copper goes.
- **Carry intent as data.** A capacitor's `Decouples` field in the schematic tells the placer which
  pin it serves, and a test checks the resulting gap.

**Try a tool before you plan around it.** The routing plan named Freerouting. In practice its CLI
crashed, it ignored inner planes, and it did not converge (ADR-019), which led to a custom grid
router. A short trial at planning time would have surfaced this earlier.

## 5. Kinds of test worth having

| Kind | What it does | Example |
| --- | --- | --- |
| Requirement as a test | Turns a limit into an assertion | `test_auw_below_ceiling`, `test_buffer_alone_keeps_fc_alive_at_hover` |
| Geometry and fit | Adds a clearance test with each new geometry step | `test_prop_tip_clears_guard`, `test_no_interference_between_any_parts` |
| Generated file in sync | Regenerates and compares | `test_generated_page_in_sync` |
| Staleness of slow results | Compares a cheap fingerprint instead of rerunning | see below |
| Tool against tool | Compares the real output of two tools | `test_kicad_step_export_matches_model` |
| Domain against domain | Connects separate disciplines | `test_betaflight_config.py`: firmware pins against schematic nets |
| Independent expected values | Derives the expected result a second way | `_expected_holes()` in `test_frame_pcb.py` |
| Solver against theory | Checks a known analytic answer | `test_cantilever_matches_beam_theory`, `test_solver_matches_hammerstad_for_thin_copper` |
| Solver against solver | Uses a second, independent solver on the same mesh | `test_thrust_deflection_matches_calculix` |
| Solver sanity | Checks physics and convergence | `test_traction_sums_to_the_load`, `test_free_body_has_six_rigid_modes`, `test_solver_converged` |
| Check of the check | Proves that a checker detects a seeded failure | `test_interference_check_detects_collisions`, `test_kicad_check_would_see_a_component_in_the_canopy` |
| Architecture | Protects the structure | `test_sizing_has_no_cad_dependency`, `test_command_module_has_main` |
| Library consistency | Checks every part's links | `test_electronics_lib.py`: symbol, footprint, 3D model, supplier number |

**Three practices worth copying:**

- **Fingerprints for slow analyses.** The FEM takes minutes, so the normal test run does not repeat
  it. `docs/structure.md` records the chassis volume, and a test compares that with the current
  model. `docs/pdn.md` records the board's SHA-256, and a test compares that with the board file.
  The test run stays fast and old results still cannot pass as current.
- **Prove that a rule fires.** KiCad's command-line DRC ignores the keep-out flags on rule areas,
  so a rule that looked active did nothing. Each new rule is now proven with a test track on a copy
  of the board. Do this whenever a check has never been seen to fail.
- **Refactors must not change numbers.** The package restructure (`plans/structure.md` S1) required
  identical STEP volumes, masses, test results and FEM values before and after.

**Analysis finds problems that geometry rules don't target.** The power distribution solver showed
that vias at 0.85 mm pitch merged their antipads into one hole in the ground plane, which doubled
one arm's return drop. The pitch became 1.3 mm (ADR-019).

**One command is the gate.** `tools/run-checks.sh` runs everything and must pass before a commit.
It writes reports to `build/reports/`.

## 6. Plans, docs and decision records

### Plans (`plans/`)

Each plan has the same structure:

```markdown
# Plan: <Area>

Goal: <one paragraph; the outcome and its limits>

**Status (YYYY-MM-DD):** <what is done, what is next>

Rules for every step:
- <e.g. values go into spec/ first; every geometry step adds a test>
- Done means: tools/run-checks.sh passes and the item is ticked here in the same commit.

Legend: **[U]** your decision or action, **[C]** Claude does it, **[U+C]** together.

---

## Phase 0: Decisions
Everything later depends on these; choose real parts, not classes.
- [x] [U] <decision>
- [x] [C] Record the decisions as ADR-00N
## Phase 1: ...
```

- Phase IDs (`E7`, `S3`, `R2`) also appear in commit subjects, ADRs and code comments, so a line of
  code can be traced back to its plan: `Electronics E7: planes, pours, critical routes...`
- Put decisions in the first phase, and put go/no-go gates in the plan where they save work. The
  full chassis print waits for S3, so no print goes into a chassis about to be replaced.
- Add a dedicated plan for a hard sub-problem: `plans/pcb-routing.md` sets the requirements and the
  method before any routing starts.
- `plans/requirements.md` gives requirements IDs (`F1`, `A1`, `P1`) and shows target against current
  estimate. It marks undecided numbers `(TBD)`, and each decision becomes an ADR.

### Docs (`docs/`)

Each page describes what currently exists and starts by naming its source:

> Generated by `uv run drone docs` from `.../system/sizing.py`; do not edit by hand
> (`tests/test_docs.py` fails when this page and the code drift apart).

State the model's accuracy on the page (here: `±25 % until thrust-stand data exists`), and don't
copy results by hand anywhere else.

### Decision records (`docs/decisions/ADR-NNN-*.md`)

Use one for any choice that isn't obvious from the code, written in the same commit as the change.
The template is short: date, status, context, decision, consequences.

What makes these useful in practice:
- **Keep what was tried.** ADR-019 records why Freerouting failed, with numbers, so nobody retries
  it blindly.
- **Date the results.** `**Result (2026-10-23):**` with measured values, not just the intention.
- **Make the status line precise.** For example `accepted; prop size and layout superseded by
  ADR-009`. Partial supersession is common, and this makes it visible.
- **Append updates.** Add a dated or named `Update` section rather than rewriting history (see
  ADR-012).
- **Mark AI decisions.** ADR-013 says `decided by Claude within the agreed scope of
  plans/structure.md; open for review`, so the person can see what still needs review.
- **List the known weak spots** under consequences.

## 7. Working with an AI assistant

**Choose tools an AI can drive.** ADR-001 made this a selection criterion: open source, scriptable,
controllable through MCP. Text file formats and command-line checks matter as much as the MCP
server does. Schematic-as-code (ADR-015) exists because editing part by part through the MCP was
slow and error-prone. Prefer one generator over many tool calls.

**Keep `CLAUDE.md` short and operational.** Include only what prevents mistakes:
- a one-paragraph summary of the product, with ADR references;
- conventions phrased as never/always, each with the command to use;
- commands, including how long the slow ones take and when they must be rerun;
- tool quirks found the hard way (each one saves a repeat of the same debugging);
- domain guard rails with numbers;
- machine-specific notes (architecture, tool paths).

Move anything longer to a plan or ADR and point to it. Add each tool quirk when you hit it.

**Make the division of labour explicit.** `[U]`, `[C]` and `[U+C]` on each checklist item let the
AI proceed without asking and show where it must stop. Reviews, purchases, physical tests and
orders are `[U]` or `[U+C]`. Claude's own review is recorded as such, and the person's review stays
an open item.

**Agree the rules, then delegate.** Load cases and limits were agreed in ADR-011 before the
optimization ran, so sizing could then run within those rules: chassis 41.8 → 32.9 g, all load
cases passing (ADR-014).

**Prototype interactively, then commit to code.** Model with the MCP, measuring and rendering after
each feature, then move the code into `src/` with a test.

**Make the work visible to a person.** Renders and schematic PDFs are regenerated by script, so
the person can review a picture rather than a 500-part netlist. `render-readme.sh` renders a clean
copy of `HEAD` by default, so images never show half-finished work.

## 8. Engineering order of work

1. Write requirements with IDs and targets. Mark unknowns `(TBD)`.
2. Build a system sizing model before any detailed design. It needs no CAD and runs in seconds.
3. Decide the architecture and interfaces, one ADR per decision. Choose real, purchasable parts,
   and check stock at this stage.
4. Set budgets and enforce them with tests (mass ceiling 300 g, ADR-017).
5. Build the parts one feature at a time, measuring after each. Report masses back to the budget.
6. Assemble digitally: interference, centre of gravity, total mass.
7. Agree load cases and limits, then analyse, then optimize.
8. Review, writing findings as a table to confirm or reject with evidence (`plans/structure.md`).
9. Test physically, feed measurements back, rerun the analyses.

Simulate the risky behaviour early. The brownout during a pack swap was simulated with ngspice
before the schematic was finished (ADR-012).

## 9. Repository mechanics

| Topic | Practice |
| --- | --- |
| Python | `uv` with a committed lockfile; pin the version and give the reason in a comment (`<3.13  # VTK / cadquery-ocp have no wheels`) |
| Commands | One CLI with a command table; import modules lazily so `drone sizing` doesn't load the CAD kernel; no-argument call lists commands |
| Shell tools | `set -euo pipefail`; resolve `ROOT` from the script; overridable tool paths (`KICAD_CLI="${KICAD_CLI:-...}"`) |
| Large files | Git LFS for STEP, STL, 3MF, FCStd, PDF, PNG, JPG |
| Text formats | `.gitattributes` keeps tool text formats as LF, so diffs stay readable |
| Ignored | Editor state, caches, tool backups and locks, all generated output; keep the folders with `.gitkeep` |
| CI | Runs in the tool's official container; uploads reports and exports as artifacts |
| Editor | Commit `.vscode/settings.json` and `extensions.json`, ignore the rest |
| Commits | Subject names the plan phase and the ADR; the plan is ticked in the same commit |

## 10. What to do better next time

These are real gaps in this repository. Most come from the same cause: **what is generated stayed
correct and what is maintained by hand drifted.**

| What happened | Evidence | Do this instead |
| --- | --- | --- |
| Status tables went stale | `plans/README.md` says electronics is at `next E2`, and `README.md` says the PCB is `next: routing`, while `plans/electronics.md` is deep in E7 | Keep status in one place and link to it, or generate the index from the plans |
| Key numbers disagree | `CLAUDE.md` says ~281 g, `plans/requirements.md` says ~289.4 g | Generate the "current estimate" column, or reference the command that prints it |
| Indexes are incomplete | `docs/README.md` omits `bom.md`, `pdn.md`, `routing.md` and `impedance.md` | Add a test that every page is listed and every page names its source |
| Stale references | `CLAUDE.md` mentions a `sim/` folder at the root (it is `electronics/power-board/sim/`); `requirements.md` still names the old `sizing.py` path; `schgen.py` cites ADR-012 instead of ADR-015; plans still say `params.py` | Add a test that paths and ADR numbers named in Markdown exist |
| Local checks and CI differ | `run-checks.sh` uses `--severity-error` and conditional parity, but `checks.yml` has its own commands | CI should call the same script |
| CI is not protecting the work | 30 commits are unpushed, so CI has not seen them; only 3 runs exist, all marked failed. In the latest, the KiCad job failed during checkout while the mechanical job passed | Get CI green in the first hour, and push often |
| Linter not enforced | `ruff` is a dependency but not in `run-checks.sh` | Add it to the check script on day one |
| Machine-specific paths | `schgen.py` hard-codes the macOS KiCad symbol path | Make every tool path overridable, as `KICAD_CLI` already is |
| Physical tests come last | Coupons and part measurements are still open while the board is at the routing stage. 9 lines in `spec/` still carry `ASSUMPTION`, and motor KV depends on a thrust test | Run cheap physical tests early, in parallel with the digital work |

## 11. Hardware stack and known pitfalls

| Need | Choice |
| --- | --- |
| Parametric CAD | build123d (Python), `build123d-mcp` |
| Electronics | KiCad 10, `kicad-cli`, KiCad MCP |
| Assembly | FreeCAD 1.1, `freecad-mcp` (generated file, never edited by hand) |
| FEM | gmsh + scikit-fem; CalculiX as a cross-check |
| Circuit simulation | ngspice, netlist in the repo, inputs from the sizing code |
| Renders | Blender Cycles, headless |
| Parts and assembly | JLCPCB/LCSC, with import and stock scripts |

**Pitfalls already paid for:**
- `kicad-cli` DRC ignores the keep-out flags on rule areas. Each keep-out also needs a custom rule
  in the `.kicad_dru` file.
- KiCad's bundled Python is separate (3.9 on macOS). Layout scripts run under it and can't import
  the main package, hence the JSON exchange file.
- Skip schematic parity in DRC until the board has footprints, or every part reports as missing.
- `freecadcmd` drops STEP colours. Build the assembly in the GUI if you want to keep them.
- VTK and OCP have no Python 3.13 wheels yet, so the mechanical environment stays on 3.12.
- The KiCad MCP's JLCPCB database download stalls. `tools/jlc_stock.py` queries stock instead.
- Freerouting does not count connections through inner planes, so dense multi-layer boards with
  planes go badly. Trial it on your board first.
- On Apple Silicon with x86_64 `node`, MCP servers' Python runs under Rosetta, so install their
  packages with `arch -x86_64`.
- Vias too close together merge their antipads into slots in the planes. The power distribution
  check caught this here, so run one on any high-current board.

**Conventions worth keeping:**
- The CAD model owns the board outline and holes; KiCad's copy is generated.
- Check printability in print orientation (no supports), from the registry.
- Keep the project's symbols, footprints and 3D models in the repo, not in global libraries.
- Every imported part's pinout gets checked against the datasheet.
- Note the datasheet section beside each value taken from it, e.g.
  `# per VCAP pin, ESR < 100 mOhm (DS12110 Table 124)`.

## 12. Starting a new project

**First hour**
- [ ] Create the layout from section 2, including `plans/README.md` and `docs/README.md` with their
      rules.
- [ ] Write `CLAUDE.md` (template below) and `ADR-000-template.md`.
- [ ] Record the tool choices as ADR-001, using "can an AI drive it?" as a criterion. Try each tool
      on a small real case.
- [ ] Set up `uv` or your stack's equivalent, the lockfile, `.gitattributes`, LFS and `.gitignore`.
- [ ] Create the single check script, including lint, and have CI call that same script. Push and
      get CI green.
- [ ] Add the Markdown integrity test (paths, ADR numbers and index completeness; section 10).

**Before detailed design**
- [ ] Write `plans/requirements.md` with IDs, targets and `(TBD)` markers.
- [ ] Create the spec layer, and fix the coordinate system or other shared conventions.
- [ ] Write the sizing or estimation model, plus requirement tests for the hard limits.
- [ ] Write one plan per area, marking each task `[U]`, `[C]` or `[U+C]`, with a decision phase first.
- [ ] Identify the riskiest assumption and schedule the cheapest real test of it now.

**During the work**
- [ ] Add a test with every step. Add a sync test at every tool boundary.
- [ ] Write an ADR with any non-obvious decision, including what was tried and failed.
- [ ] Tick the plan in the same commit. Name the phase in the commit subject.
- [ ] Add each tool quirk to `CLAUDE.md` when you hit it.
- [ ] Replace `ASSUMPTION` values with measurements as they arrive, and rerun the analyses.

### Applying this outside hardware

| Here | Pure software equivalent |
| --- | --- |
| `spec/` dimensions | Typed config, schemas, API contracts |
| CAD ↔ KiCad sync tests | Schema ↔ client, migration ↔ model, and config ↔ deployment sync tests |
| FEM and solver validation | Benchmarks and known-answer tests for algorithms or models |
| Mass and current budgets | Latency, memory and cost budgets as tests |
| Physical prototypes | Production-like trials and load tests with real data |

## 13. Templates

### `CLAUDE.md`

```markdown
# CLAUDE.md

<Two or three lines on what this is, with ADR references for each major choice.>

## Conventions
- All shared values live in `<spec path>`. Never hard-code them elsewhere; add to the spec first.
- Package layers, imports only point downwards: `spec` → ... → `cli.py`.
- Generated (never edit by hand): `<files>`. Change `<source>`, run `<command>`, commit both.
- Generated output (`build/`, ...) is never committed.
- Non-obvious design choices get an ADR in `docs/decisions/` (copy `ADR-000-template.md`).
- `plans/` holds intent; `docs/` holds only what code and tools produce, plus ADRs.
  Results never go into a plan; a plan item links to the doc or ADR.
- Tick a plan item in the same commit that completes it.

## Commands
- Checks: `tools/run-checks.sh`. Must pass before commit.
- `<command>`: <what it does, how long it takes, when it must be rerun>.

## Tools
- `<MCP server or tool>`: <what it is for; known limits>.

## Machine notes
- <architecture, install paths, quirks>

## Guard rails
- <domain limits with numbers, and the test or doc that enforces each one>
```

### `docs/decisions/ADR-000-template.md`

```markdown
# ADR-NNN: Title

- Date: YYYY-MM-DD
- Status: proposed | accepted | superseded by ADR-XXX

## Context
What problem or constraint forces a decision? What was tried?

## Decision
What we chose.

## Consequences
What becomes easier or harder; follow-up work; known weak spots.
```

### `plans/README.md` rules

```markdown
Rules:
- A plan lists intent and checklist items; it does not hold results. Results go into `docs/`
  (generated where possible) or into an ADR, and the plan item links to them.
- Tick an item in the same commit that completes it; update the plan's status line when a phase
  finishes.
- Legend in every plan: **[U]** your decision or action, **[C]** Claude does it, **[U+C]** together.
- Finished or superseded plans move to `archive/`.
```

### Tests for generated pages and slow results

```python
@pytest.mark.parametrize("name", PAGES)
def test_generated_page_in_sync(name):
    assert (DOCS_DIR / name).read_text() == PAGES[name](), f"run `uv run <cli> docs` ({name})"


def test_slow_result_belongs_to_the_current_input():
    sha = hashlib.sha256(INPUT_FILE.read_bytes()).hexdigest()
    assert f"`{sha}`" in RESULT_PAGE.read_text(), "rerun `uv run <cli> <analysis>`"
```

### Layer boundary test

```python
def test_low_layer_has_no_heavy_dependency():
    code = "import sys, pkg.system.sizing; print('heavy_lib' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
```

### One CLI with lazy imports

```python
COMMANDS = {"sizing": ("pkg.system.sizing", "budgets"), "docs": ("pkg.io.docs", "regenerate docs/")}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("commands:", *(f"  {k}  {v[1]}" for k, v in COMMANDS.items()), sep="\n")
        sys.exit(0 if len(sys.argv) < 2 else 2)
    module, _ = COMMANDS[sys.argv[1]]
    sys.argv = [f"cli {sys.argv[1]}", *sys.argv[2:]]
    importlib.import_module(module).main()
```

### Check script

```bash
#!/usr/bin/env bash
# Every check in one place. CI calls this script too. Non-zero exit on any violation.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
status=0
(cd "$ROOT" && uv run ruff check .) || status=1
(cd "$ROOT" && uv run pytest -q)    || status=1
# Domain checks (ERC, DRC, ...) go here; write their reports to build/reports/
exit $status
```
