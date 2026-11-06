"""Requirements are tests. A second group checks the physics of the model itself."""

import pytest

from vawt import spec
from vawt.spec import CHARGER, GENERATOR, PROTECTION, ROTOR, SITE
from vawt.system import sizing as z
from vawt.system.requirements import REQUIREMENTS, Requirement


@pytest.mark.parametrize("req", REQUIREMENTS, ids=lambda r: r.id)
def test_requirement_holds(req):
    assert req.holds(), f"{req.id} {req.text}: {req.value():.3g} against {req.limit:.3g}"


def test_ids_are_unique():
    ids = [r.id for r in REQUIREMENTS]
    assert len(ids) == len(set(ids))


def test_a_broken_limit_is_seen():
    """Check of the check: a requirement that cannot hold reports that."""
    assert not Requirement("X", "x", "", 1.0, "max", lambda: 2.0, "E").holds()
    assert not Requirement("X", "x", "", 3.0, "min", lambda: 2.0, "E").holds()


def test_cp_peaks_at_the_best_tip_speed_ratio():
    assert z.cp(ROTOR.tsr_opt) == pytest.approx(ROTOR.cp_max)
    assert z.cp(0.0) == 0.0
    assert z.cp(ROTOR.tsr_no_load) == 0.0
    assert z.cp(ROTOR.tsr_opt) > z.cp(ROTOR.tsr_opt * 0.8)
    assert z.cp(ROTOR.tsr_opt) > z.cp(ROTOR.tsr_opt * 1.2)


def test_torque_coefficient_is_continuous_at_standstill():
    assert z.cq(0.0) == pytest.approx(z.cq(1e-4), rel=1e-3)


def test_rotor_power_stays_below_what_the_model_allows():
    for v in (3.0, 8.0, 15.0):
        p = z.best_point(v)
        assert p.torque * p.rpm / z.RPM_PER_RAD_S <= ROTOR.cp_max * z.wind_power(v) * 1.001


def test_power_grows_with_wind():
    powers = [z.best_point(float(v)).charge for v in range(4, 15)]
    assert powers == sorted(powers)


def test_operating_points_stay_inside_every_limit():
    """Firmware cannot use a point the hardware would refuse, at any wind."""
    for tenths in range(20, 301, 5):
        p = z.best_point(tenths / 10, steps=300)
        if p.charge == 0:
            continue
        assert CHARGER.vbus_min <= p.vbus < z.relay_trip_voltage(), tenths
        assert p.current <= GENERATOR.rated_current_a, tenths
        assert p.copper <= GENERATOR.copper_limit_w, tenths


def test_energy_balance_at_the_operating_point():
    """Mechanical power must equal electrical power, copper and the diodes, independently summed."""
    v = 10.0
    p = z.best_point(v)
    mechanical = p.torque * p.rpm / z.RPM_PER_RAD_S
    diodes = 2 * PROTECTION.schottky_vf * p.current
    electrical = p.vbus * p.current
    assert mechanical == pytest.approx(electrical + p.copper + diodes, rel=1e-6)


def test_rayleigh_integrates_to_one_with_the_right_mean():
    dv = 0.01
    speeds = [i * dv for i in range(1, 6000)]
    assert sum(z.rayleigh_pdf(v, 3.5) * dv for v in speeds) == pytest.approx(1.0, rel=1e-3)
    assert sum(v * z.rayleigh_pdf(v, 3.5) * dv for v in speeds) == pytest.approx(3.5, rel=1e-3)


def test_cantilever_matches_beam_theory():
    """F L^3 / (3 E I) for a known case, computed from first principles."""
    length = spec.rotor_centre_z()
    force = z.rotor_drag_n(SITE.survival_wind_m_s)
    expected = force * length**3 / (3 * SITE.wood_e_mpa * SITE.pier_width**4 / 12)
    assert z.rotor_drag_n(SITE.survival_wind_m_s) / z.pier_stiffness_n_mm() == pytest.approx(
        expected
    )


def test_relay_protects_before_the_charger_stops():
    assert z.relay_trip_voltage() < CHARGER.acovp < CHARGER.vbus_abs_max


def test_helix_runs_on_unbroken_across_sections():
    assert spec.section_rotation_deg(1) == pytest.approx(ROTOR.section_pitch / 3)


def test_stack_height_matches_the_3mf_top_cap():
    """The blades end where the 3MF puts the cap: its 15 mm centred 2.5 mm below their top."""
    top_of_blades = ROTOR.section_height + ROTOR.section_pitch * ROTOR.middle_sections
    assert top_of_blades == pytest.approx(ROTOR.top_centre_z + 2.5)
