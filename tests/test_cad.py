"""What FreeCAD built, read from build/cad/report.json. `tools/run-checks.sh` rebuilds it first."""

import hashlib
import json
from pathlib import Path

import pytest

from vawt import spec
from vawt.spec import BOARD, ENCLOSURE, PRINTER, ROTOR, SITE

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build" / "cad" / "report.json"


@pytest.fixture(scope="module")
def report():
    if not REPORT.exists():
        pytest.fail("no CAD report: run tools/build-cad.sh")
    return json.loads(REPORT.read_text())


def test_report_belongs_to_the_current_sources(report):
    h = hashlib.sha256()
    for path in [ROOT / "src/vawt/spec.py", *sorted((ROOT / "cad/freecad").glob("*.py"))]:
        h.update(path.read_bytes())
    assert report["fingerprint"] == h.hexdigest(), "stale: run tools/build-cad.sh"


def test_nothing_collides(report):
    hits = {
        k: v
        for k, v in report["checks"].items()
        if v > 0.01 and k != "seeded_overlap_must_be_positive"
    }
    assert not hits, f"overlaps in mm3: {hits}"


def test_the_collision_check_can_fail(report):
    """Check of the check: a box known to sit in the tub's wall is found, at its true volume."""
    assert report["checks"]["seeded_overlap_must_be_positive"] == pytest.approx(200.0, rel=0.01)


def test_every_part_is_one_valid_solid(report):
    for name, part in report["parts"].items():
        assert part["valid"], name
        assert part["solids"] == 1, f"{name} has {part['solids']} solids"


def test_every_part_fits_the_print_bed(report):
    for name, part in report["parts"].items():
        assert max(part["size_mm"]) <= PRINTER.bed, name


def test_enclosure_takes_all_expected_parts(report):
    assert {"tub", "lid", "rain_hood"} <= set(report["parts"])
    assert max(report["parts"]["tub"]["size_mm"]) == pytest.approx(
        spec.enclosure_total_height(), abs=0.1
    )


def test_rotor_meshes_stand_where_the_spec_says(report):
    if not report["vendored"]:
        pytest.skip("the licensed 3MF is not on this machine")
    rotor = report["rotor"]
    assert rotor["z_min"] == pytest.approx(spec.rotor_bottom_z(), abs=0.1)
    assert rotor["z_max"] == pytest.approx(spec.rotor_bottom_z() + spec.rotor_height(), abs=0.1)
    assert rotor["max_radius"] == pytest.approx(ROTOR.diameter / 2, abs=0.3)


def test_rotor_tip_really_clears_the_pier(report):
    if not report["vendored"]:
        pytest.skip("the licensed 3MF is not on this machine")
    assert -SITE.pier_width / 2 - report["rotor"]["tip_y_max"] >= 15.0


def test_upper_bracket_sits_on_the_pier_below_its_top(report):
    if not report["vendored"]:
        pytest.skip("the licensed 3MF is not on this machine")
    bracket = report["bracket_top"]
    assert bracket["y_max"] == pytest.approx(-SITE.pier_width / 2, abs=0.05)
    assert bracket["z_max"] <= SITE.pier_height
    assert bracket["z_min"] > report["rotor"]["z_max"]


def test_kicad_board_stands_where_the_enclosure_expects_it(report):
    """Tool against tool: the STEP KiCad exported, seen from FreeCAD, against spec."""
    board = report["board"]
    assert board["real_geometry"], "run tools/build-electronics.sh, then tools/build-cad.sh"
    assert board["x"] == pytest.approx([-BOARD.width / 2, BOARD.width / 2], abs=0.6)
    # Taller parts than the spec says would make ENC3 a false promise
    tallest = board["y_top_local"] - (ENCLOSURE.wall + ENCLOSURE.pcb_standoff + BOARD.thickness)
    assert tallest <= BOARD.tallest_top


def test_fcstd_exists(report):
    assert (ROOT / "build" / "cad" / "wind-turbine.FCStd").exists()
