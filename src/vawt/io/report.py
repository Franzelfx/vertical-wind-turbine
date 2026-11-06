"""Builds the booklet for friends: `uv run vawt pdf` writes build/report/vertical-wind-turbine.pdf.

Every figure reaches `report/booklet.typ` through build/report/data.json, from the spec, the sizing
model, the requirements and the generated pages (ADR-009). Needs ImageMagick's `magick`, and the dev
group's matplotlib and typst, which load inside the functions so importing this stays cheap.
"""

import json
import os
import re
import subprocess
from datetime import date
from math import exp, pi
from pathlib import Path

from vawt import spec
from vawt.spec import (
    BATTERY,
    BOARD,
    BRACKET,
    CHARGER,
    DRIVE,
    ENCLOSURE,
    GENERATOR,
    LAYOUT,
    PRINTER,
    PROTECTION,
    ROTOR,
    SITE,
    YARDSTICK,
)
from vawt.system import requirements as rq
from vawt.system import sizing as z

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "report" / "booklet.typ"
OUT = ROOT / "build" / "report"
PDF = OUT / "vertical-wind-turbine.pdf"
MAGICK = os.environ.get("MAGICK", "magick")
HOURS_A_YEAR = 8760
NBSP = " "
ACCENT = "#1F5A96"  # the rotor's blue; checked with the dataviz palette validator
INK = "#20272E"
MUTED = "#5B6670"
HAIRLINE = "#D5DBE0"
BAND = "#F3F5F7"
# Name and upper limit in m/s of each Beaufort force the chart reaches: a standard scale
BEAUFORT = (
    ("light", 3.3),
    ("gentle", 5.4),
    ("moderate", 7.9),
    ("fresh", 10.7),
    ("strong", 13.8),
    ("near gale", 17.1),
    ("gale", 20.7),
)
# Source picture and width in pixels: full-page pictures keep their size, the rest need less
PICTURES = {
    "render-site": 1800,
    "render-site-labelled": 1800,
    "render-turbine": 1200,
    "render-turbine-top": 1200,
    "render-drive": 1200,
    "render-drive-open": 1200,
    "render-enclosure": 1200,
    "render-enclosure-below": 1200,
    "render-enclosure-open": 1400,
    "render-enclosure-exploded": 1400,
}


def q(value: float, digits: int, unit: str = "") -> str:
    """A number with its unit, which never parts from it at a line end."""
    return f"{value:.{digits}f}{NBSP}{unit}" if unit else f"{value:.{digits}f}"


def md_tables(path: Path) -> list[list[list[str]]]:
    """Each Markdown table of a page, as rows of cells, without its header's rule."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in [*path.read_text().splitlines(), ""]:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables


def plain(cell: str) -> str:
    """A cell without repository paths and code marks: readers of the booklet have no repository."""
    cell = re.sub(r" \(`[^`]*`\)", "", cell)
    cell = re.sub(r", `electronics/.*$", "", cell)
    return cell.replace("`", "").replace("**", "")


def plan_progress() -> list[dict]:
    """Ticked items per phase of each plan. Bench tests have no phases: they count as one."""
    phases = []
    for page in ("mechanical", "electronics"):
        title, done, total = "", 0, 0
        for line in [*(ROOT / "plans" / f"{page}.md").read_text().splitlines(), "## Phase end: "]:
            match = re.match(r"## Phase (\w+): (.*)", line)
            if match:
                if title:
                    phases.append({"title": title, "done": done, "total": total})
                title, done, total = f"{match[1]}  {plain(match[2])}", 0, 0
            elif line.startswith("- ["):
                total += 1
                done += line.startswith("- [x]")
    bench = re.findall(r"^- \[(.)\]", (ROOT / "plans" / "bench.md").read_text(), re.MULTILINE)
    phases.append(
        {"title": "B1-B6  Bench tests", "done": bench.count("x"), "total": len(bench)},
    )
    return phases


def decisions() -> list[list[str]]:
    rows = []
    for path in sorted((ROOT / "docs" / "decisions").glob("ADR-*.md")):
        if "000" in path.name:
            continue
        text = path.read_text()
        number, title = re.match(r"# (ADR-\d+): (.*)", text).groups()
        status = re.search(r"^- Status: (.*)$", text, re.MULTILINE)[1]
        who = "Chosen by the project's owner" if "accepted" in status else "Proposed by Claude (AI)"
        rows.append([number, title, who])
    return rows


def wind_bands(mean: float | None = None) -> list[dict]:
    """Hours and energy a year in each 1 m/s band, on the same steps as the yield calculation."""
    mean = SITE.mean_wind_m_s if mean is None else mean
    bands = [
        {"low": low, "hours": 0.0, "wh": 0.0} for low in range(int(SITE.survival_wind_m_s) + 1)
    ]
    dv = 0.5
    v = dv
    while v <= SITE.survival_wind_m_s:
        band = bands[int((v - 1e-9) // 1)]
        hours = z.rayleigh_pdf(v, mean) * dv * HOURS_A_YEAR
        band["hours"] += hours
        band["wh"] += z.best_point(v, steps=200).charge * hours
        v += dv
    return bands


def share_above(v: float, mean: float | None = None) -> float:
    """Share of the time the wind blows above v: the Rayleigh distribution's upper tail."""
    mean = SITE.mean_wind_m_s if mean is None else mean
    return exp(-pi * v**2 / (4 * mean**2))


def half_energy_wind(bands: list[dict]) -> int:
    """The band's lower edge above which half of the year's energy arrives."""
    total = sum(b["wh"] for b in bands)
    running = 0.0
    for band in reversed(bands):
        running += band["wh"]
        if running >= total / 2:
            return band["low"]
    return 0


def power_rows() -> list[list[str]]:
    rows = []
    for v in (3, 4, 5, 6, 8, 10, 12, 15, 17, 18, 20):
        p = z.best_point(float(v))
        rows.append(
            [
                str(v),
                f"{p.rpm:.0f}",
                f"{p.torque:.3f}",
                f"{p.current:.2f}",
                f"{p.vbus:.1f}",
                f"{p.copper:.1f}",
                f"{p.charge:.1f}",
            ]
        )
    return rows


def yield_rows() -> list[list[str]]:
    return [
        [
            f"{mean}",
            f"{z.mean_charge_power(mean):.2f}",
            f"{z.annual_energy_kwh(mean):.1f}",
            f"{z.days_to_fill(mean):.0f}",
        ]
        for mean in (2.5, 3.5, 4.5, 5.5)
    ]


def structure_rows() -> list[list[str]]:
    survival = SITE.survival_wind_m_s
    return [
        ["Rotor drag", q(z.rotor_drag_n(survival), 0, "N")],
        ["Pier drag", q(z.pier_drag_n(survival), 0, "N")],
        ["Moment at the pier's base", q(z.pier_base_moment_nm(survival), 0, "N m")],
        ["Bending stress at the base", q(z.pier_base_stress_mpa(survival), 1, "MPa")],
        ["Pier utilisation, EN 1995 style", q(z.pier_utilisation(survival), 2)],
        ["Deflection at rotor height", q(z.pier_deflection_mm(survival), 0, "mm")],
        ["Bracket arm stress", q(z.bracket_stress_mpa(survival), 1, "MPa")],
        ["M8 stub stress", q(z.shaft_stress_mpa(survival), 0, "MPa")],
    ]


def requirement_rows() -> list[list[str]]:
    rows = []
    for r in rq.REQUIREMENTS:
        sign = "≤" if r.sense == "max" else "≥"
        unit = f"{NBSP}{r.unit}" if r.unit else ""
        rows.append(
            [
                r.id,
                r.text.replace("`", ""),
                f"{sign} {r.limit:.4g}{unit}",
                f"{r.value():.4g}{unit}",
                r.evidence,
                "yes" if r.holds() else "NO",
            ]
        )
    return rows


def assumption_rows() -> list[list[str]]:
    rows = md_tables(ROOT / "docs" / "assumptions.md")[0][1:]
    return [[plain(a).replace("_", " "), plain(b)] for a, b in rows]


def print_rows() -> list[list[str]]:
    rows = md_tables(ROOT / "docs" / "printing.md")[0][1:]
    return [
        [plain(part).replace("_", " ").capitalize(), n, material, how, size, supports.split(",")[0]]
        for part, n, material, how, size, _, supports in rows
    ]


def bom_rows() -> list[list[str]]:
    rows = md_tables(ROOT / "docs" / "bom.md")[0][1:]
    return [
        [plain(parts), n, plain(value), plain(lcsc), plain(mpn), line]
        for parts, n, value, lcsc, mpn, _, _, line in rows
    ]


def version() -> str:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()

    dirty = " with local changes" if git("status", "--porcelain") else ""
    return f"{date.today().isoformat()}, from commit {git('rev-parse', '--short', 'HEAD')}{dirty}"


def data() -> dict:
    survival = SITE.survival_wind_m_s
    peak = z.peak_charge()
    start, stop = z.charging_wind_range()
    bands = wind_bands()
    mean_w = z.mean_charge_power()
    kwh = z.annual_energy_kwh()
    solar_kwh = YARDSTICK.solar_panel_w * YARDSTICK.solar_kwh_per_kwp / 1000
    braked_rpm, braked_w = z.braked_rpm(10.0)
    bom = (ROOT / "docs" / "bom.md").read_text()
    board_usd = re.search(r"Parts total: about ([\d.]+) USD", bom)[1]
    bom_date = re.search(r"Stock and prices as of ([\d-]+)", bom)[1]
    hardware = md_tables(ROOT / "docs" / "hardware.md")
    return {
        "version": version(),
        "accuracy": "±50 %",
        # Site and rotor
        "pier_height": q(SITE.pier_height / 1000, 0, "m"),
        "rotor_h": q(spec.rotor_height(), 0, "mm"),
        "rotor_size": f"{ROTOR.diameter:.0f}{NBSP}×{NBSP}{spec.rotor_height():.0f}{NBSP}mm",
        "rotor_mass": q(spec.rotor_mass_kg(), 2, "kg"),
        "rotor_bottom": q(spec.rotor_bottom_z() / 1000, 2, "m"),
        "tip_clearance": q(spec.rotor_tip_clearance(), 1, "mm"),
        "reach": q(BRACKET.axis_to_plate, 0, "mm"),
        "cp": q(ROTOR.cp_max, 2),
        "tsr": q(ROTOR.tsr_opt, 1),
        "bearing_spacing": q(DRIVE.bearing_spacing, 0, "mm"),
        "torque_8": q(z.best_point(8.0).torque, 2, "N m"),
        "wind_eight": q(8.0, 0, "m/s"),
        "stub_stress": q(z.shaft_stress_mpa(survival), 0, "MPa"),
        # Wind and power
        "cut_in": q(start, 1, "m/s"),
        "peak_w": q(peak.charge, 1, "W"),
        "peak_wind": q(peak.wind, 1, "m/s"),
        "peak_bus": q(peak.vbus, 0, "V"),
        "mean_wind": q(SITE.mean_wind_m_s, 1, "m/s"),
        "mean_w": q(mean_w, 2, "W"),
        "kwh_year": q(kwh, 1, "kWh"),
        "days_fill": q(z.days_to_fill(), 0, "days"),
        "charging_share": q(100 * share_above(start), 0, "%"),
        "wind_ten": q(10.0, 0, "m/s"),
        "hours_above_10": q(HOURS_A_YEAR * share_above(10.0), 0, "hours"),
        "half_energy_wind": q(half_energy_wind(bands), 0, "m/s"),
        "half_energy_share": q(100 * share_above(half_energy_wind(bands)), 0, "%"),
        "yield_rows": yield_rows(),
        "power_rows": power_rows(),
        # Yardsticks
        "phones_in_pack": q(spec.battery_wh() / YARDSTICK.phone_wh, 0),
        "euro_year": f"€{kwh * YARDSTICK.electricity_eur_kwh:.1f}0",
        "euro_kwh": f"€{YARDSTICK.electricity_eur_kwh:.2f}",
        "solar_w": q(YARDSTICK.solar_panel_w, 0, "W"),
        "solar_kwh": q(solar_kwh, 0, "kWh"),
        "solar_ratio": q(solar_kwh / kwh, 0),
        # Battery
        "pack_wh": q(spec.battery_wh(), 0, "Wh"),
        "pack_range": (f"{spec.battery_v_empty():.1f}-{spec.battery_v_full():.1f}{NBSP}V"),
        "pack_cells": f"{BATTERY.cells_series}S{BATTERY.cells_parallel}P",
        "standby": q(z.quiescent_power_mw(), 2, "mW"),
        "standby_years": q(z.self_discharge_days() / 365, 0, "years"),
        "temp_min": q(BATTERY.charge_temp_min_c, 0, "°C"),
        "temp_max": q(BATTERY.charge_temp_max_c, 0, "°C"),
        # Generator and electronics
        "generator": GENERATOR.name,
        "kv": q(GENERATOR.kv_rpm_per_v, 0, "rpm/V"),
        "gen_mass": q(GENERATOR.mass_kg * 1000, 0, "g"),
        "gen_current": q(GENERATOR.rated_current_a, 1, "A"),
        "gen_copper": q(GENERATOR.copper_limit_w, 0, "W"),
        "charger_min": q(CHARGER.vbus_min, 1, "V"),
        "charger_max": q(CHARGER.vbus_max, 0, "V"),
        "efficiency": q(100 * CHARGER.efficiency, 0, "%"),
        "relay_trip": q(z.relay_trip_voltage(), 1, "V"),
        "relay_parts": q(PROTECTION.schottky_vr, 0, "V"),
        "relay_watts": q(z.series_resistor_power(z.open_circuit_bus(survival)), 1, "W"),
        "coil_mw": q(z.relay_leak_w(12.0) * 1000, 0, "mW"),
        "bus_ref": q(12.0, 0, "V"),
        "wind_charger_limit": q(z.wind_at_charger_limit(), 1, "m/s"),
        "bus_survival": q(z.open_circuit_bus(survival), 0, "V"),
        "board_size": f"{BOARD.width:.0f}{NBSP}×{NBSP}{BOARD.height:.0f}{NBSP}mm",
        "board_usd": f"{board_usd}{NBSP}USD",
        "bom_date": bom_date,
        # Stopping and storms
        "survival": q(survival, 0, "m/s"),
        "free_limit_wind": q(ROTOR.max_rpm / z.free_running_rpm(1.0), 0, "m/s"),
        "brake_rpm": q(braked_rpm, 0, "rpm"),
        "brake_w": q(braked_w, 1, "W"),
        "brake_wind": q(10.0, 0, "m/s"),
        "brake_limit_wind": q(z.highest_wind_for_brake(), 1, "m/s"),
        "pin": q(DRIVE.lock_pin_dia - 0.2, 0, "mm"),
        "fall_zone": q(SITE.pier_height / 1000, 0, "m"),
        "utilisation": q(z.pier_utilisation(survival), 2),
        "deflection": q(z.pier_deflection_mm(survival), 0, "mm"),
        # Vibration
        "mode_hz": q(z.pier_first_mode_hz(), 1, "Hz"),
        "mode_rpm": q(z.resonance_rpm(), 0, "rpm"),
        "mode_wind": q(z.resonance_wind(), 1, "m/s"),
        "swing": q(z.resonance_amplitude_mm(), 1, "mm"),
        # Enclosure
        "box_size": (
            f"{spec.enclosure_flange_width():.0f}{NBSP}×{NBSP}"
            f"{spec.enclosure_total_height():.0f}{NBSP}mm"
        ),
        "box_height": q(LAYOUT.enclosure_centre_z / 1000, 2, "m"),
        "gasket": q(ENCLOSURE.gasket_cord_dia, 0, "mm"),
        "squeeze": q(100 * (1 - ENCLOSURE.gasket_groove_depth / ENCLOSURE.gasket_cord_dia), 0, "%"),
        "standoff": q(ENCLOSURE.standoff_from_wood, 0, "mm"),
        "hood_gap": q(ENCLOSURE.hood_gap, 0, "mm"),
        "bed": q(PRINTER.bed, 0, "mm"),
        # Tables taken whole
        "structure_rows": structure_rows(),
        "requirement_rows": requirement_rows(),
        "requirements_total": str(len(rq.REQUIREMENTS)),
        "assumption_rows": assumption_rows(),
        "assumptions_total": str(len(assumption_rows())),
        "mechanical_rows": [[plain(c) for c in row] for row in hardware[1][1:]],
        "electrical_rows": [[plain(c) for c in row] for row in hardware[2][1:]],
        "print_rows": print_rows(),
        "bom_rows": bom_rows(),
        "decision_rows": decisions(),
        "progress": plan_progress(),
    }


def draw_chart(path: Path) -> None:
    """Three small multiples on one wind axis: power x hours = energy. One colour."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "Avenir Next",
            "font.size": 8,
            "svg.fonttype": "path",
            "axes.edgecolor": HAIRLINE,
            "axes.linewidth": 0.6,
            "axes.titlesize": 9,
            "axes.titlelocation": "left",
            "axes.titleweight": "demibold",
            "axes.titlecolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
        }
    )
    limit = 20.0
    winds = [0.25 * i for i in range(1, int(limit * 4) + 1)]
    power = [z.best_point(v, steps=300).charge for v in winds]
    peak = z.peak_charge()
    bands = [b for b in wind_bands() if b["low"] < limit]
    centres = [b["low"] + 0.5 for b in bands]
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(6.69, 5.2), height_ratios=[1.45, 1, 1])
    for ax in axes:
        low = 0.0
        for i, (_, high) in enumerate(BEAUFORT):
            if i % 2 == 0:
                ax.axvspan(low, min(high, limit), color=BAND, lw=0, zorder=0)
            low = high
        ax.grid(axis="y", color=HAIRLINE, lw=0.5, zorder=1)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.set_xlim(0, limit)
    # Power
    ax = axes[0]
    ax.plot(winds, power, color=ACCENT, lw=1.6, zorder=3)
    ax.set_ylim(0, 25)
    ax.set_yticks([0, 10, 20])
    ax.set_title("Power into the battery at each wind speed, in watts", pad=16)
    low = 0.0
    for name, high in BEAUFORT:
        ax.text((low + min(high, limit)) / 2, 25.6, name, ha="center", va="bottom", color=MUTED)
        low = high
    ax.annotate(
        f"{peak.charge:.1f} W at best",
        xy=(peak.wind, peak.charge),
        xytext=(peak.wind - 0.5, peak.charge + 2.4),
        ha="right",
        color=INK,
        arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.5},
    )
    ax.text(17.45, 7, "relay opens:\nrotor runs free", color=INK, va="center", linespacing=1.3)
    # Hours
    ax = axes[1]
    ax.bar(centres, [b["hours"] for b in bands], width=0.8, color=ACCENT, zorder=3)
    ax.set_title(f"Hours a year at each speed, if the mean wind is {SITE.mean_wind_m_s} m/s")
    # Energy
    ax = axes[2]
    ax.bar(centres, [b["wh"] for b in bands], width=0.8, color=ACCENT, zorder=3)
    ax.set_title("So the energy a year from each speed, in watt-hours: power × hours")
    ax.set_xlabel("Wind speed (m/s)", color=MUTED)
    ax.set_xticks(range(0, int(limit) + 1, 2))
    fig.subplots_adjust(left=0.06, right=0.975, top=0.91, bottom=0.085, hspace=0.42)
    fig.savefig(path, transparent=True)
    plt.close(fig)


def write_pictures(folder: Path) -> None:
    """Smaller JPEG copies of the renders, remade only when a source is newer."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, width in PICTURES.items():
        source = ROOT / "docs" / "images" / f"{name}.png"
        target = folder / f"{name}.jpg"
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            continue
        subprocess.run(
            [
                MAGICK,
                str(source),
                "-resize",
                f"{width}x",
                "-quality",
                "86",
                "-sampling-factor",
                "4:2:0",
                str(target),
            ],
            check=True,
        )


def build() -> list[str]:
    """Writes the PDF and returns Typst's warnings."""
    import typst

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(data(), indent=1, ensure_ascii=False))
    draw_chart(OUT / "power.svg")
    write_pictures(OUT / "images")
    pdf, warnings = typst.compile_with_warnings(str(TEMPLATE), root=str(ROOT), format="pdf")
    PDF.write_bytes(pdf)
    return [w.message for w in warnings]


def main() -> None:
    warnings = build()
    for message in warnings:
        print("warning:", message)
    print(f"wrote {PDF.relative_to(ROOT)}, {PDF.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
