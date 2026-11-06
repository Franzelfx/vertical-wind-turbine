"""The booklet builds cleanly, and its prose takes every figure from the model."""

import json
import re

import pytest

from vawt import spec
from vawt.io import report
from vawt.system import sizing as z

# A number with a unit. Layout lengths in the template use pt, cm and em, never these.
TYPED_FIGURE = re.compile(
    r"(?<![\w.#])\d+(?:\.\d+)?[ ~]?"
    r"(?:m/s|kWh|Wh|mW|W|kW|V|A|Ah|kg|g|rpm|MPa|mm|m|days|hours|years|degC|°C|USD|EUR)\b"
)


def test_no_figure_typed_in_the_template():
    source = report.TEMPLATE.read_text()
    prose = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("//"))
    assert not TYPED_FIGURE.findall(prose), "add these to data() in src/vawt/io/report.py"


def test_wind_bands_add_up_to_the_year():
    bands = report.wind_bands()
    assert sum(b["wh"] for b in bands) / 1000 == pytest.approx(z.annual_energy_kwh())
    assert sum(b["hours"] for b in bands) == pytest.approx(report.HOURS_A_YEAR, rel=0.01)


def test_plan_progress_counts_every_item():
    ticks = 0
    for page in ("mechanical", "electronics", "bench"):
        text = (report.ROOT / "plans" / f"{page}.md").read_text()
        ticks += len(re.findall(r"^- \[", text, re.MULTILINE))
    assert sum(p["total"] for p in report.plan_progress()) == ticks


def test_every_decision_is_listed():
    records = list((report.ROOT / "docs" / "decisions").glob("ADR-*.md"))
    assert len(report.decisions()) == len(records) - 1  # without the template


def test_booklet_builds_without_warnings():
    assert report.build() == []
    assert report.PDF.read_bytes().startswith(b"%PDF")
    data = json.loads((report.OUT / "data.json").read_text())
    assert data["pack_wh"].startswith(f"{spec.battery_wh():.0f}")
