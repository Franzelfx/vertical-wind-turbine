"""The schematic and board, read from what KiCad reports. Needs `tools/build-electronics.sh`."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from vawt.spec import BATTERY, BOARD, CHARGER, PROTECTION

ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = ROOT / "electronics" / "charge-board"
REPORTS = ROOT / "build" / "reports"
NETLIST = ROOT / "build" / "kicad" / "charge-board.net.xml"


@pytest.fixture(scope="module")
def net():
    if not NETLIST.exists():
        pytest.fail("no netlist: run tools/build-electronics.sh")
    root = ET.parse(NETLIST).getroot()
    comps = {c.get("ref"): c.findtext("value") for c in root.find("components")}
    pins = {}
    for n in root.find("nets"):
        for node in n:
            pins[(node.get("ref"), node.get("pin"))] = n.get("name").split("/")[-1]
    return comps, pins


def _ref(comps, value):
    return next(ref for ref, v in comps.items() if v == value)


def test_erc_is_clean():
    report = json.loads((REPORTS / "erc.json").read_text())
    errors = [v for sheet in report["sheets"] for v in sheet["violations"]]
    assert not errors, errors


def test_drc_is_clean_apart_from_open_connections():
    report = json.loads((REPORTS / "drc.json").read_text())
    assert report["violations"] == []
    assert report["schematic_parity"] == [], "board and schematic disagree"


def test_charger_is_programmed_for_3s(net):
    comps, pins = net
    prog = next(n for key, n in pins.items() if n == "PROG" and key[0].startswith("R"))
    assert prog == "PROG"
    r = next(key[0] for key, n in pins.items() if n == "PROG" and key[0].startswith("R"))
    assert comps[r] == f"{CHARGER.prog_ohm / 1000:.1f}k"
    assert CHARGER.cells == BATTERY.cells_series


def test_relay_common_is_the_bus_and_normally_closed_feeds_the_charger(net):
    comps, pins = net
    k = _ref(comps, "SRD-12VDC-SL-C")
    assert pins[(k, "1")] == "BUS_RAW"
    assert pins[(k, "4")] == "VBUS_IN"
    assert (k, "3") not in pins or pins[(k, "3")].startswith("unconnected")


def test_relay_series_resistors_match_the_spec(net):
    comps, pins = net
    series = [ref for ref, v in comps.items() if v.endswith("3W") and ref.startswith("R")]
    assert len(series) == 3
    each = float(comps[series[0]].split("k")[0]) * 1000
    assert each / 3 == pytest.approx(PROTECTION.relay_series_ohm)
    for ref in series:
        assert {pins[(ref, "1")], pins[(ref, "2")]} == {"BUS_RAW", "COIL_P"}


def test_every_terminal_in_the_spec_exists_in_the_schematic(net):
    comps, _ = net
    values = set(comps.values())
    for name, _x in BOARD.terminals:
        assert name in values, name


def test_tvs_protects_the_charger_side_only(net):
    comps, pins = net
    d = _ref(comps, "SMBJ26CA")
    assert "VBUS_IN" in {pins[(d, "1")], pins[(d, "2")]}


def test_mcu_can_wake_on_the_charger_interrupt(net):
    """ESP32-C3 deep sleep only wakes on GPIO 0-5."""
    comps, pins = net
    u = _ref(comps, "ESP32-C3-WROOM-02")
    assert pins[(u, "15")] == "CHG_INT"  # IO3


def test_board_outline_matches_the_spec():
    text = (BOARD_DIR / "charge-board.kicad_pcb").read_text()
    segments = re.findall(
        r"\(gr_line\s+\(start ([-\d.]+) ([-\d.]+)\)\s+\(end ([-\d.]+) ([-\d.]+)\)"
        r".*?\(layer \"Edge\.Cuts\"\)",
        text,
        re.DOTALL,
    )
    assert len(segments) == 4
    xs = [float(v) for s in segments for v in (s[0], s[2])]
    ys = [float(v) for s in segments for v in (s[1], s[3])]
    assert max(xs) - min(xs) == pytest.approx(BOARD.width)
    assert max(ys) - min(ys) == pytest.approx(BOARD.height)


def test_generated_schematic_is_not_hand_edited():
    """Regeneration gives identical files: UUIDs derive from references, so a diff is real."""
    before = {p.name: p.read_text() for p in BOARD_DIR.glob("*.kicad_sch")}
    assert len(before) == 4
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, str(BOARD_DIR / "schematic" / "build.py")], check=True, capture_output=True
    )
    after = {p.name: p.read_text() for p in BOARD_DIR.glob("*.kicad_sch")}
    assert before == after


def test_bq25798_symbol_matches_the_datasheet_pinout():
    """Independent expected values: typed from SLUSDV2C Table 5-1, not read from the symbol."""
    table_5_1 = {
        "STAT": ["1"], "VBUS": ["2", "3"], "BTST1": ["4"], "REGN": ["5"], "D+": ["6"], "D-": ["7"],
        "VAC2": ["8"], "VAC1": ["9"], "ACDRV2": ["10"], "ACDRV1": ["11"], "~{QON}": ["12"],
        "~{CE}": ["13"], "SCL": ["14"], "SDA": ["15"], "TS": ["16"], "ILIM_HIZ": ["17"],
        "BATP": ["18"], "BTST2": ["19"], "PROG": ["20"], "~{INT}": ["21"], "BAT": ["22", "23"],
        "SDRV": ["24"], "SYS": ["25"], "SW2": ["26"], "GND": ["27"], "SW1": ["28"], "PMID": ["29"],
    }  # fmt: skip
    text = (ROOT / "electronics" / "lib" / "symbols" / "vawt.kicad_sym").read_text()
    found: dict[str, list[str]] = {}
    for name, number in re.findall(r'\(name "([^"]+)".*?\(number "(\d+)"', text, re.DOTALL):
        found.setdefault(name, []).append(number)
    assert {k: sorted(v, key=int) for k, v in found.items()} == table_5_1


def test_bom_snapshot_lists_every_part(net):
    comps, _ = net
    page = (ROOT / "docs" / "bom.md").read_text()
    listed = set(re.findall(r"\b[A-Z]+\d+\b", page))
    for ref in comps:
        if not ref.startswith("H"):  # mounting holes are not parts
            assert ref in listed, f"{ref}: run tools/bom.py"


def test_bom_snapshot_has_no_part_out_of_stock():
    page = (ROOT / "docs" / "bom.md").read_text()
    assert "**none**" not in page, "a part is out of stock: choose another"
