"""Requirements as data: each has an ID, a limit and a live value. Generates plans/requirements.md.

`tests/test_requirements.py` fails if any limit is broken. All of these hold on paper only: nothing
has been built yet. `evidence` is M (measured from a real file), S (source quoted) or E (estimate).
"""

from collections.abc import Callable
from dataclasses import dataclass

from vawt import spec
from vawt.spec import (
    BATTERY,
    BOARD,
    BRACKET,
    CHARGER,
    ENCLOSURE,
    GENERATOR,
    PRINTER,
    PROTECTION,
    ROTOR,
    SITE,
)
from vawt.system import sizing as z


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    unit: str
    limit: float
    sense: str  # "max": value must not exceed the limit; "min": must not fall below
    value: Callable[[], float]
    evidence: str

    def holds(self) -> bool:
        v = self.value()
        return v <= self.limit if self.sense == "max" else v >= self.limit


def _survival_power() -> float:
    return z.series_resistor_power(z.open_circuit_bus(SITE.survival_wind_m_s))


REQUIREMENTS = [
    Requirement(
        "SYS1",
        "Charge voltage: 3S Li-ion, the `12 V` pack in the brief",
        "V",
        BATTERY.cells_series * BATTERY.v_full_cell,
        "max",
        lambda: CHARGER.v_reg,
        "S",
    ),
    Requirement("SYS2", "Mean wind fills the pack in", "days", 14.0, "max", z.days_to_fill, "E"),
    Requirement(
        "SYS3",
        "Pack drain with the rotor standing: charger, regulator, MCU, BMS",
        "mW",
        1.0,
        "max",
        z.quiescent_power_mw,
        "E",
    ),
    Requirement("SYS4", "Wind at which charging begins", "m/s", 4.0, "max", z.cut_in_wind, "E"),
    Requirement(
        "SYS5",
        "Wind at which the rotor starts against cogging and drag",
        "m/s",
        3.0,
        "max",
        z.start_wind,
        "E",
    ),
    Requirement(
        "ELE1",
        "Relay trips below the charger's overvoltage stop",
        "V",
        CHARGER.acovp,
        "max",
        z.relay_trip_voltage,
        "E",
    ),
    Requirement(
        "ELE2",
        "Open-circuit bus at survival wind, within the 100 V parts",
        "V",
        PROTECTION.schottky_vr,
        "max",
        lambda: z.open_circuit_bus(SITE.survival_wind_m_s),
        "E",
    ),
    Requirement(
        "ELE3",
        "Relay series resistors at survival wind",
        "W",
        PROTECTION.relay_series_watt,
        "max",
        _survival_power,
        "E",
    ),
    Requirement(
        "ELE4",
        "Generator current at peak power, within the motor's rating",
        "A",
        GENERATOR.rated_current_a,
        "max",
        lambda: z.peak_charge().current,
        "E",
    ),
    Requirement(
        "ELE5",
        "Generator copper loss at peak power",
        "W",
        GENERATOR.copper_limit_w,
        "max",
        lambda: z.peak_charge().copper,
        "E",
    ),
    Requirement(
        "ELE6",
        "Charger input current at peak power",
        "A",
        CHARGER.ibus_max,
        "max",
        lambda: z.peak_charge().current,
        "S",
    ),
    Requirement("MEC1", "Rotor tip to pier face", "mm", 15.0, "min", spec.rotor_tip_clearance, "M"),
    Requirement(
        "MEC2",
        "Rotor underside above ground, out of reach",
        "mm",
        2000.0,
        "min",
        spec.rotor_bottom_z,
        "M",
    ),
    Requirement(
        "MEC3",
        "Longest printed enclosure part on the print bed",
        "mm",
        PRINTER.bed,
        "max",
        spec.enclosure_total_height,
        "M",
    ),
    Requirement(
        "MEC4",
        "Enclosure screws stay on the pier's face",
        "mm",
        SITE.pier_width,
        "max",
        lambda: ENCLOSURE.ear_hole_spacing + ENCLOSURE.ear_hole_dia + 2 * 3.0,
        "M",
    ),
    Requirement(
        "MEC5",
        "Pier utilisation at survival wind, EN 1995 style",
        "",
        1.0,
        "max",
        lambda: z.pier_utilisation(SITE.survival_wind_m_s),
        "E",
    ),
    Requirement(
        "MEC6",
        "Swing at the rotor when imbalance sits on the pier's first mode",
        "mm",
        5.0,
        "max",
        z.resonance_amplitude_mm,
        "E",
    ),
    Requirement(
        "MEC7",
        "Bracket arm bending at survival wind, ASA with layer knock-down",
        "MPa",
        10.0,
        "max",
        lambda: z.bracket_stress_mpa(SITE.survival_wind_m_s),
        "E",
    ),
    Requirement(
        "MEC8",
        "M8 stub bending at survival wind, A2-70",
        "MPa",
        200.0,
        "max",
        lambda: z.shaft_stress_mpa(SITE.survival_wind_m_s),
        "E",
    ),
    Requirement(
        "MEC9",
        "Wind at which a free-running rotor reaches its speed limit: lock it above",
        "m/s",
        20.0,
        "min",
        lambda: ROTOR.max_rpm / z.free_running_rpm(1.0),
        "E",
    ),
    Requirement(
        "ENC1",
        "Gasket squeeze, lower bound",
        "%",
        20.0,
        "min",
        lambda: 100 * (1 - ENCLOSURE.gasket_groove_depth / ENCLOSURE.gasket_cord_dia),
        "M",
    ),
    Requirement(
        "ENC2",
        "Gasket squeeze, upper bound",
        "%",
        35.0,
        "max",
        lambda: 100 * (1 - ENCLOSURE.gasket_groove_depth / ENCLOSURE.gasket_cord_dia),
        "M",
    ),
    Requirement(
        "ENC3",
        "Tallest board part to the lid's inner face",
        "mm",
        5.0,
        "min",
        lambda: (
            spec.enclosure_tub_depth()
            + ENCLOSURE.lid_inner_depth
            - (ENCLOSURE.wall + ENCLOSURE.pcb_standoff + BOARD.thickness + BOARD.tallest_top)
        ),
        "M",
    ),
]

_ = BRACKET  # geometry lives in spec; this module only compares it


def table() -> str:
    lines = [
        "| ID | Requirement | Limit | Now | Holds | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in REQUIREMENTS:
        sign = "<=" if r.sense == "max" else ">="
        verdict = "yes" if r.holds() else "**NO**"
        unit = f" {r.unit}" if r.unit else ""
        lines.append(
            f"| {r.id} | {r.text} | {sign} {r.limit:.4g}{unit} | {r.value():.4g}{unit} | {verdict} "
            f"| {r.evidence} |"
        )
    return "\n".join(lines)
