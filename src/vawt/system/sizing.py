"""Power, voltage and structure sizing with no CAD. Runs in milliseconds.

The rotor is a parabola in tip speed ratio, the generator a back-EMF behind a resistance. A real
torque-speed curve (bench test B3) replaces the rotor model and resistance measurement (B1) the
generator's; until then treat every power figure as +-50 %.
"""

from dataclasses import dataclass
from math import exp, pi, sqrt

from vawt import spec
from vawt.spec import BRACKET, CHARGER, GENERATOR, PROTECTION, ROTOR, SITE

RPM_PER_RAD_S = 60 / (2 * pi)


def cp(tsr: float) -> float:
    """Power coefficient: parabola with its peak at tsr_opt, zero at standstill and at no load."""
    if tsr <= 0 or tsr >= ROTOR.tsr_no_load:
        return 0.0
    x = (tsr - ROTOR.tsr_opt) / ROTOR.tsr_opt
    return ROTOR.cp_max * (1 - x**2)


def cq(tsr: float) -> float:
    """Torque coefficient, Cp / tsr. Its limit at standstill is 2 cp_max / tsr_opt."""
    if tsr <= 1e-6:
        return 2 * ROTOR.cp_max / ROTOR.tsr_opt
    return cp(tsr) / tsr


def dynamic_force_scale(v: float) -> float:
    """1/2 rho A v^2, in newton."""
    return 0.5 * SITE.air_density * spec.swept_area_m2() * v**2


def rotor_torque(v: float, omega: float) -> float:
    """Torque on the shaft in N m at wind speed v (m/s) and rotor speed omega (rad/s)."""
    radius = ROTOR.diameter / 2000
    tsr = omega * radius / v if v > 0 else 0.0
    return cq(tsr) * dynamic_force_scale(v) * radius


def wind_power(v: float) -> float:
    return dynamic_force_scale(v) * v


def rpm_at_tsr(v: float, tsr: float) -> float:
    return tsr * v / (ROTOR.diameter / 2000) * RPM_PER_RAD_S


@dataclass(frozen=True)
class OperatingPoint:
    wind: float
    rpm: float
    torque: float
    current: float
    vbus: float
    copper: float
    charge: float


def relay_leak_w(bus: float) -> float:
    """What the relay's coil path draws below pick-up, while the rotor runs: a few percent."""
    return bus**2 / (PROTECTION.relay_series_ohm + PROTECTION.relay_coil_ohm)


def best_point(v: float, steps: int = 800) -> OperatingPoint:
    """Ideal input-voltage tracking: the best charge power that stays within every limit.

    Scans rotor speed and picks the point with the highest power. Speed, torque, generator current
    and bus voltage follow from one another. Limits: the charger's minimum input; the relay's trip
    voltage, which comes before the charger's maximum; the generator's current and copper loss,
    which firmware must hold by letting the rotor run faster at lower torque (ADR-007).
    """
    k = spec.generator_k()
    radius = ROTOR.diameter / 2000
    omega_max = ROTOR.tsr_no_load * v / radius if v > 0 else 0.0
    best = OperatingPoint(v, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    for i in range(1, steps):
        omega = omega_max * i / steps
        torque = rotor_torque(v, omega) - GENERATOR.drag_nm
        if torque <= 0:
            continue
        current = torque / k  # line current through the bridge
        vbus = k * omega - 2 * PROTECTION.schottky_vf - current * GENERATOR.resistance_ll_ohm
        if not CHARGER.vbus_min <= vbus < min(CHARGER.vbus_max, relay_trip_voltage()):
            continue
        if current > min(CHARGER.ibus_max, GENERATOR.rated_current_a):
            continue
        if current**2 * GENERATOR.resistance_ll_ohm > GENERATOR.copper_limit_w:
            continue
        charge = (vbus * current - relay_leak_w(vbus)) * CHARGER.efficiency
        if charge > best.charge:
            best = OperatingPoint(
                v,
                omega * RPM_PER_RAD_S,
                torque,
                current,
                vbus,
                current**2 * GENERATOR.resistance_ll_ohm,
                charge,
            )
    return best


def peak_charge() -> OperatingPoint:
    """The most power the system can deliver at any wind, within every limit."""
    winds = [0.5 * i for i in range(2, int(2 * SITE.survival_wind_m_s) + 1)]
    return max((best_point(v, steps=400) for v in winds), key=lambda p: p.charge)


def charging_wind_range() -> tuple[float, float]:
    """Lowest and highest wind with any charging. Above the top, the relay opens."""
    winds = [0.1 * i for i in range(10, int(10 * SITE.survival_wind_m_s) + 1)]
    charging = [v for v in winds if best_point(v, steps=200).charge > 0]
    return charging[0], charging[-1]


def cut_in_wind() -> float:
    """Lowest wind that charges at all, with 0.1 m/s resolution."""
    v = 1.0
    while v < 15.0:
        if best_point(v).charge > 0:
            return v
        v += 0.1
    return float("inf")


def start_wind() -> float:
    """Lowest wind whose standstill torque overcomes cogging."""
    radius = ROTOR.diameter / 2000
    needed = (GENERATOR.cogging_nm + GENERATOR.drag_nm) / (cq(0.0) * radius)
    return sqrt(needed / (0.5 * SITE.air_density * spec.swept_area_m2()))


def rayleigh_pdf(v: float, mean: float) -> float:
    return pi * v / (2 * mean**2) * exp(-pi * v**2 / (4 * mean**2))


def mean_charge_power(mean_wind: float | None = None) -> float:
    """Average charge power over a Rayleigh wind distribution, in watt."""
    mean = SITE.mean_wind_m_s if mean_wind is None else mean_wind
    dv = 0.5
    total = 0.0
    v = dv
    while v <= SITE.survival_wind_m_s:
        total += best_point(v, steps=200).charge * rayleigh_pdf(v, mean) * dv
        v += dv
    return total


def annual_energy_kwh(mean_wind: float | None = None) -> float:
    return mean_charge_power(mean_wind) * 8760 / 1000


def free_running_rpm(v: float) -> float:
    return rpm_at_tsr(v, ROTOR.tsr_no_load)


def open_circuit_bus(v: float) -> float:
    """Rectified voltage of the unloaded generator with the rotor free-running at wind v."""
    return free_running_rpm(v) / GENERATOR.kv_rpm_per_v


def wind_at_charger_limit() -> float:
    """Wind at which a free-running rotor pushes the open-circuit bus past the charger's maximum."""
    return CHARGER.vbus_max * GENERATOR.kv_rpm_per_v / free_running_rpm(1.0)


def relay_trip_voltage() -> float:
    """Bus voltage at which the coil reaches pick-up through its series resistor."""
    current = PROTECTION.relay_pickup_v / PROTECTION.relay_coil_ohm
    return PROTECTION.relay_pickup_v + current * PROTECTION.relay_series_ohm


def relay_trip_current_ma() -> float:
    return PROTECTION.relay_pickup_v / PROTECTION.relay_coil_ohm * 1000


def series_resistor_power(bus: float) -> float:
    """Power in the coil's series resistor with the 12 V zener holding the coil at nominal."""
    return (bus - PROTECTION.relay_coil_v) ** 2 / PROTECTION.relay_series_ohm


def braked_rpm(v: float, series_ohm: float = PROTECTION.brake_ohm) -> tuple[float, float]:
    """Rotor speed and generator copper power with the bus shorted through the brake resistor."""
    k = spec.generator_k()
    radius = ROTOR.diameter / 2000
    omega_max = ROTOR.tsr_no_load * v / radius
    total_r = GENERATOR.resistance_ll_ohm + series_ohm
    low, high = 0.0, omega_max
    for _ in range(60):  # rotor torque falls with speed, brake torque rises: one crossing
        omega = (low + high) / 2
        current = max(k * omega - 2 * PROTECTION.schottky_vf, 0.0) / total_r
        if k * current > rotor_torque(v, omega):
            high = omega
        else:
            low = omega
    current = max(k * low - 2 * PROTECTION.schottky_vf, 0.0) / total_r
    return low * RPM_PER_RAD_S, current**2 * GENERATOR.resistance_ll_ohm


def highest_wind_for_brake(limit_w: float = GENERATOR.copper_limit_w) -> float:
    """Highest wind at which the brake keeps the generator within its copper limit."""
    v = 1.0
    while v < SITE.survival_wind_m_s and braked_rpm(v)[1] <= limit_w:
        v += 0.1
    return v


# --- structure -----------------------------------------------------------------------------------


def rotor_drag_n(v: float, cd: float = 1.2) -> float:
    """Drag on the rotor, in newton. Cd 1.2 is the usual figure for a Savonius-like body."""
    return cd * dynamic_force_scale(v)


def pier_drag_n(v: float, cd: float = 1.5) -> float:
    """Drag on the square pier, in newton. Cd 1.5 is a sharp-edged square section."""
    area = SITE.pier_width * SITE.pier_height * 1e-6
    return cd * 0.5 * SITE.air_density * area * v**2


def pier_section_modulus() -> float:
    return SITE.pier_width**3 / 6


def pier_second_moment() -> float:
    return SITE.pier_width**4 / 12


def pier_base_moment_nm(v: float) -> float:
    return rotor_drag_n(v) * spec.rotor_centre_z() / 1000 + pier_drag_n(v) * SITE.pier_height / 2000


def pier_base_stress_mpa(v: float) -> float:
    return pier_base_moment_nm(v) * 1000 / pier_section_modulus()


def pier_design_strength_mpa() -> float:
    """EN 1995 style: fm,k x kmod 0.9 (short-term, class 3 is 0.7 for long-term) / gamma_M 1.3."""
    return SITE.wood_fmk_mpa * 0.9 / 1.3


def pier_utilisation(v: float) -> float:
    """Design stress with gamma_Q 1.5 over design strength."""
    return 1.5 * pier_base_stress_mpa(v) / pier_design_strength_mpa()


def pier_deflection_mm(v: float) -> float:
    """Deflection at the rotor's height: rotor point load; the pier's own drag is added crudely."""
    a = spec.rotor_centre_z()
    ei = SITE.wood_e_mpa * pier_second_moment()
    return rotor_drag_n(v) * a**3 / (3 * ei) + pier_drag_n(v) * SITE.pier_height**3 / (8 * ei) * (
        a / SITE.pier_height
    )


def pier_mass_kg() -> float:
    volume = SITE.pier_width**2 * SITE.pier_height * 1e-9
    return volume * SITE.wood_density_kg_m3


def pier_first_mode_hz(guyed: bool = False) -> float:
    """First bending mode: tip mass on a cantilever, Rayleigh's 33/140 for the pier's own mass."""
    h = SITE.pier_height / 1000
    ei = SITE.wood_e_mpa * 1e6 * pier_second_moment() * 1e-12
    stiffness = 3 * ei / h**3
    if guyed:
        # Pinned at the guy attachment, about 2.2 m up, the mode has a node there: much stiffer.
        h = 2.2
        stiffness = 48 * ei / h**3
    tip = spec.rotor_mass_kg() + GENERATOR.mass_kg + 0.5
    mass = tip + 33 / 140 * pier_mass_kg()
    return sqrt(stiffness / mass) / (2 * pi)


def resonance_rpm() -> float:
    """Rotor speed at which once-per-turn imbalance drives the pier's first mode."""
    return pier_first_mode_hz() * 60


def resonance_wind() -> float:
    """Wind at which the rotor reaches that speed at its best tip speed ratio."""
    return resonance_rpm() / rpm_at_tsr(1.0, ROTOR.tsr_opt)


def bracket_load_n(v: float) -> float:
    """Horizontal load on one of the two bearing supports."""
    return rotor_drag_n(v) / 2


def bracket_stress_mpa(v: float) -> float:
    """Bending at the original bracket's arm root, wind across the arm: hub plate as a beam."""
    moment = bracket_load_n(v) * BRACKET.axis_to_plate
    w = BRACKET.hub_thickness * BRACKET.arm_width**2 / 6
    return moment / w


def shaft_stress_mpa(v: float) -> float:
    """Bending in the M8 stub, 15 mm from the hub to the bearing's centre, at the thread's root."""
    moment = bracket_load_n(v) * 15.0
    root_dia = 6.466  # ISO 724 M8 minor diameter
    return moment * 32 / (pi * root_dia**3)


def centrifugal_stress_mpa(rpm: float, density: float = 1070.0) -> float:
    """rho v^2 at the tip, in the wall, for ASA: the part of the load that needs no shape factor.

    The real wall also bends between its joints, so bench test B4 sets the limit, not this.
    """
    tip = rpm / RPM_PER_RAD_S * ROTOR.diameter / 2000
    return density * tip**2 / 1e6


def imbalance_force_n(rpm: float) -> float:
    """Once-per-turn force from the assumed imbalance."""
    omega = rpm / RPM_PER_RAD_S
    return ROTOR.imbalance_g_mm * 1e-6 * omega**2


def pier_stiffness_n_mm() -> float:
    """Static stiffness at the rotor's centre height."""
    a = spec.rotor_centre_z()
    return 3 * SITE.wood_e_mpa * pier_second_moment() / a**3


def resonance_amplitude_mm() -> float:
    """Swing at the rotor when once-per-turn imbalance sits exactly on the pier's first mode."""
    return imbalance_force_n(resonance_rpm()) * ROTOR.damping_q / pier_stiffness_n_mm()


def days_to_fill(mean_wind: float | None = None) -> float:
    return spec.battery_wh() / (mean_charge_power(mean_wind) * 24)


def quiescent_power_mw() -> float:
    """Pack drain with no wind: charger + 3.3 V regulator + MCU in deep sleep + BMS."""
    regulator_ua = 22.0  # AP63203 datasheet, no-load input current
    mcu_ua = 5.0 * 3.3 / spec.battery_v_nominal()  # ESP32-C3 deep sleep through the buck
    bms_ua = 10.0  # ASSUMPTION: typical cheap 3S BMS; B2
    return (
        (CHARGER.iq_battery_ua + regulator_ua + mcu_ua + bms_ua) * spec.battery_v_nominal() / 1000
    )


def self_discharge_days() -> float:
    return spec.battery_wh() * 1000 / quiescent_power_mw() / 24


def main() -> None:
    print(
        f"Rotor   {ROTOR.diameter:.0f} x {spec.rotor_height():.0f} mm, swept "
        f"{spec.swept_area_m2():.3f} m2, {spec.rotor_mass_kg():.2f} kg at the slicer's settings"
    )
    print(
        f"Position: underside at z = {spec.rotor_bottom_z():.0f} mm, axis at y = "
        f"{spec.rotor_axis_y():.0f} mm, {spec.rotor_tip_clearance():.1f} mm tip to pier"
    )
    print(f"Starts at {start_wind():.1f} m/s, charges from {cut_in_wind():.1f} m/s")
    print(" wind  rpm  torque     I   VBUS copper charge")
    for v in (3, 4, 5, 6, 8, 10, 12, 15, 18, 20):
        p = best_point(float(v))
        print(
            f"{v:5.0f} {p.rpm:4.0f} {p.torque:7.3f} {p.current:5.2f} {p.vbus:6.1f} "
            f"{p.copper:6.1f} {p.charge:6.1f}"
        )
    peak = peak_charge()
    print(
        f"Peak {peak.charge:.1f} W at {peak.wind:.1f} m/s, up to {charging_wind_range()[1]:.1f} m/s"
    )
    print(
        f"Yield at {SITE.mean_wind_m_s} m/s mean wind: {mean_charge_power():.2f} W, "
        f"{annual_energy_kwh():.1f} kWh/year; pack fills in {days_to_fill():.0f} days"
    )
    print(
        f"Open-circuit bus at {SITE.survival_wind_m_s:.0f} m/s: "
        f"{open_circuit_bus(SITE.survival_wind_m_s):.0f} V; passes the charger's "
        f"{CHARGER.vbus_max:.0f} V at {wind_at_charger_limit():.1f} m/s"
    )
    print(f"Relay trips at {relay_trip_voltage():.1f} V")
    print(
        f"Pier at {SITE.survival_wind_m_s:.0f} m/s: "
        f"{pier_base_moment_nm(SITE.survival_wind_m_s):.0f}"
        f" N m at the base, utilisation {pier_utilisation(SITE.survival_wind_m_s):.2f}, "
        f"{pier_deflection_mm(SITE.survival_wind_m_s):.0f} mm deflection"
    )
    print(
        f"First pier mode {pier_first_mode_hz():.1f} Hz = {resonance_rpm():.0f} rpm, reached at "
        f"{resonance_wind():.1f} m/s; swing at resonance {resonance_amplitude_mm():.1f} mm; "
        f"guyed {pier_first_mode_hz(guyed=True):.1f} Hz"
    )


if __name__ == "__main__":
    main()
