"""Every shared number of the project. Nothing outside this file hard-codes one (ADR-002).

Pure data, standard library only: FreeCAD's bundled Python imports this file too.

Units are millimetres unless a name says otherwise. Anything not measured or taken from a named
source carries the literal word ASSUMPTION and the bench test that will replace it
(`plans/bench.md`); `uv run vawt docs` lists them all in `docs/assumptions.md`.

Coordinates (world): z up, origin on the pier axis at ground level. The turbine stands on the -y
side of the pier, the enclosure on the +y side. Rotor frame: same axes, origin on the rotor axis at
the underside of the bottom section.
"""

from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class Site:
    pier_width: float = 80.0  # given by the user
    pier_height: float = 3000.0  # above ground, given by the user
    wood_density_kg_m3: float = 450.0  # EN 338 C24, mean is 420; rounded up for wet timber
    wood_e_mpa: float = 11000.0  # EN 338 C24, E0,mean
    wood_fmk_mpa: float = 24.0  # EN 338 C24, characteristic bending strength
    air_density: float = 1.225  # kg/m3, ISA sea level
    mean_wind_m_s: float = 3.5  # ASSUMPTION: 3 m mast in a garden; replace with a site log (B5)
    survival_wind_m_s: float = 30.0  # ASSUMPTION: 11 Bft gust, typical inland Germany upper bound


@dataclass(frozen=True)
class Rotor:
    """GeoJolt's "Ugrinsky Style wind Turbine" (MakerWorld 861294). Measured from the 3MF meshes."""

    diameter: float = 245.0  # measured: bounding radius 122.5
    section_height: float = 225.0  # measured
    section_pitch: float = 220.0  # 3MF source offsets 112.5 / 332.5: sections overlap 5 mm
    middle_sections: int = 3  # top cap at source offset 882.5 means 1 bottom + 3 middle
    top_centre_z: float = 882.5  # 3MF source offset of the top cap
    top_height: float = 15.0  # measured
    twist_deg_per_mm: float = 1.0 / 3.0  # measured: 6.25 deg per 18.74 mm
    bearing_seat_dia: float = 22.1  # measured: suits a 608 bearing, 22 x 7 mm
    bearing_seat_depth: float = 8.0  # measured, bottom section; seat opens downwards
    floor_thickness: float = 5.5  # measured: bore wall starts ~5.5 mm above the underside
    bore_dia: float = 43.0  # measured: free core of the sections
    mass_bottom_kg: float = 0.40647  # slicer, 3MF slice_info: 0.12 mm, 2 walls, 15 % infill
    mass_middle_kg: float = 0.40789  # slicer
    mass_top_kg: float = 0.05810  # slicer
    # Performance. A 2-D CFD study reports Cp 0.170 for the Ugrinsky profile (WIT ESUS21); 2-D CFD
    # flatters, and wind-tunnel Savonius rotors of this size reach about 0.118.
    cp_max: float = 0.12  # ASSUMPTION: replace with the torque-speed curve from bench test B3
    tsr_opt: float = 0.8  # ASSUMPTION: typical of drag rotors; B3
    tsr_no_load: float = 1.6  # ASSUMPTION: twice tsr_opt, parabolic model; B3
    max_rpm: float = 3000.0  # ASSUMPTION: bench spin test B4 sets the real limit
    damping_q: float = 20.0  # ASSUMPTION: timber pier, about 2.5 % damping; B5
    imbalance_g_mm: float = 500.0  # ASSUMPTION: 5 g at 100 mm for an unbalanced print; B4


@dataclass(frozen=True)
class OriginalBracket:
    """The model's own wall bracket, used unchanged at the top. Measured from the mesh."""

    axis_to_plate: float = 140.0  # 3MF source offset +60 with the plate back face at +80
    plate_width: float = 60.0  # measured
    plate_height: float = 75.0  # measured
    plate_thickness: float = 10.0  # measured
    hole_pattern: float = 40.0  # measured: holes at +-20 in both directions
    hole_dia: float = 8.1  # measured
    hub_radius: float = 20.0  # measured
    hub_thickness: float = 15.5  # measured
    bore_dia: float = 8.2  # measured
    gap_to_rotor: float = 5.0  # 3MF source offset: top of the arm is 5 mm below the rotor
    arm_width: float = 40.0  # measured at the hub
    mass_kg: float = 0.05596  # slicer


@dataclass(frozen=True)
class Layout:
    """Where things sit on the pier."""

    top_bracket_margin: float = 20.0  # top bracket stops this far below the pier top
    enclosure_centre_z: float = 1350.0  # chest height, reachable without a ladder
    cable_conduit_dia: float = 16.0  # M16 flexible conduit


@dataclass(frozen=True)
class DriveTrain:
    """The new parts that take torque from the rotor down to the generator (ADR-004)."""

    # Drive flange: replaces the bottom bearing, bolted through the rotor floor
    flange_dia: float = 60.0
    flange_thickness: float = 8.0
    flange_skirt_height: float = 5.5  # drip edge outside the housing, stops above the arm
    flange_boss_dia: float = 22.0  # locates in the rotor's bearing seat
    flange_bolt_pcd: float = 34.0  # lands on the floor between seat and bore wall
    flange_bolt_dia: float = 4.3  # M4 through-bolts
    flange_bolts: int = 3
    lock_pin_dia: float = 6.2  # parking pin through flange and housing, ADR-005
    lock_pin_pcd: float = 46.0
    # Bearing housing, on the same 140 mm reach as the original bracket
    shaft_dia: float = 8.0  # M8 rod, A2 stainless
    bearing_od: float = 22.0  # 608
    bearing_seat_dia: float = 22.1  # same fit as the model's seats
    bearing_width: float = 7.0
    bearing_spacing: float = 48.0  # centre to centre
    housing_od: float = 40.0
    housing_top_gap: float = 6.0  # flange underside to housing top; the skirt overlaps the gap
    arm_width: float = 26.0
    arm_rib_thickness: float = 8.0
    plate_width: float = 60.0  # same as the original, fits the 80 mm pier
    plate_height: float = 120.0
    plate_thickness: float = 10.0
    plate_hole_dia: float = 8.1  # M8 coach screws, as in the original bracket
    plate_hole_pattern_w: float = 40.0
    plate_hole_pattern_h: float = 90.0
    # Generator cage and cover
    coupling_length: float = 26.0  # TPU spider between rod and bell
    coupling_dia: float = 34.0
    cage_post_dia: float = 10.0
    cage_pcd: float = 62.0
    cage_plate_thickness: float = 6.0
    cover_wall: float = 2.5
    cover_clearance: float = 2.0
    cover_overlap: float = 16.0  # cover slides this far up over the housing, rain side


@dataclass(frozen=True)
class Generator:
    """iPower/iFlight GM4108H-120T gimbal motor (24N22P)."""

    name: str = "GM4108H-120T"
    # Retailer listings give 1025-1089 rpm at 20 V
    kv_rpm_per_v: float = 52.85
    resistance_ll_ohm: float = 11.0  # ASSUMPTION: no published figure found; measure, B1
    inductance_ll_h: float = 0.005  # ASSUMPTION: B1
    cogging_nm: float = 0.012  # ASSUMPTION: low for a 24N22P gimbal motor; B1
    drag_nm: float = 0.010  # ASSUMPTION: three bearings plus iron loss; B1
    rated_current_a: float = 1.5  # listing: load current 1.5 A
    copper_limit_w: float = 12.0  # ASSUMPTION: thermal limit of a 124 g motor in free air; B2
    diameter: float = 47.0  # listing
    height: float = 32.3  # iFlight 32.3 mm with the shaft; RobotShop 47 x 24 mm body
    mass_kg: float = 0.124  # iFlight
    bore_dia: float = 8.0  # iFlight: hollow shaft ID 8 +0.05
    pole_pairs: int = 11  # 22 poles


@dataclass(frozen=True)
class Charger:
    """BQ25798, datasheet SLUSDV2C (datasheets/bq25798-SLUSDV2C.pdf)."""

    vbus_min: float = 3.6  # 6.3 recommended operating conditions
    vbus_max: float = 24.0  # 6.3
    vbus_abs_max: float = 30.0  # 6.1
    acovp: float = 26.0  # 4 device comparison, default
    ibus_max: float = 3.3  # 6.3
    iq_battery_ua: float = 17.0  # 6.5 IQ_BAT_ON, ADC off
    efficiency: float = 0.85  # ASSUMPTION: at light load and large step; B2
    prog_ohm: float = 13700.0  # Table 7-1: 750 kHz, 3S
    cells: int = 3
    v_reg: float = 12.6  # Table 7-2: 3S default


@dataclass(frozen=True)
class Protection:
    """Input stage, ADR-006: a self-powered relay isolates the charger above the trip voltage."""

    schottky_vf: float = 0.45  # SS510, 5 A 100 V, at about 1 A
    schottky_vr: float = 100.0  # SS510
    relay_coil_v: float = 12.0  # Songle SRD-12VDC-SL-C
    relay_coil_ohm: float = 400.0  # SRD datasheet: 0.36 W at 12 V
    relay_pickup_v: float = 9.0  # SRD datasheet: at most 75 % of nominal; measure the real one, B2
    relay_series_ohm: float = 600.0  # three 1.8 kohm 3 W axials in parallel
    relay_series_watt: float = 9.0
    relay_contact_a: float = 10.0  # SRD datasheet at 30 V DC
    brake_ohm: float = 4.7
    brake_watt: float = 25.0


@dataclass(frozen=True)
class Battery:
    """3S2P 18650 pack with its own BMS. "12 V Li-ion" in the brief means this: 9.0-12.6 V."""

    cells_series: int = 3
    cells_parallel: int = 2
    cell_ah: float = 3.5  # ASSUMPTION: LG MJ1 / Samsung 35E class; check the bought pack
    v_nominal_cell: float = 3.6
    v_full_cell: float = 4.2
    v_empty_cell: float = 3.0
    length: float = 72.0  # pack with BMS and wrap; ASSUMPTION: measure the bought pack
    height: float = 60.0
    depth: float = 42.0
    mass_kg: float = 0.32  # 6 x 48 g + BMS
    fuse_a: float = 7.5  # mini blade fuse at the pack
    charge_temp_min_c: float = 0.0  # Li-ion must not charge below 0 degC: TS pin, NTC on the pack
    charge_temp_max_c: float = 45.0


@dataclass(frozen=True)
class Board:
    """The charge board, KiCad project in electronics/charge-board/."""

    width: float = 100.0
    height: float = 80.0
    thickness: float = 1.6
    hole_inset: float = 4.0
    hole_dia: float = 3.2
    tallest_top: float = 17.5  # measured: KiCad's STEP export reaches 17.2; tests/test_cad.py
    tallest_bottom: float = 2.5
    # Terminal blocks along the lower edge, board x of each centre. KiCad places them from here and
    # CAD runs the wires to them. Seen from the front of the box, board x is mirrored (ADR-007).
    terminals: tuple = (
        ("GENERATOR", -32.0),
        ("BRAKE", -15.0),
        ("PACK", 2.0),
        ("PACK_NTC", 14.0),
        ("LOAD", 26.0),
    )


@dataclass(frozen=True)
class Enclosure:
    """Printed in ASA. Tub plus lid, gasket on the rim, no opening on the top face."""

    inner_width: float = 116.0
    inner_height: float = 176.0
    tub_inner_depth: float = 40.0
    lid_inner_depth: float = 12.0
    wall: float = 3.0
    corner_radius: float = 6.0
    flange: float = 13.0  # rim outside the walls carries screws and gasket
    flange_corner_radius: float = 8.0
    flange_thickness: float = 5.0
    gasket_groove_width: float = 3.4
    gasket_groove_depth: float = 2.2
    gasket_cord_dia: float = 3.0  # EPDM cord; squeeze = 1 - depth / cord, checked in tests
    gasket_offset: float = 2.7  # groove centre, outside the wall's outer face
    rim_screw_dia: float = 4.3  # M4 clearance through the lid
    rim_insert_dia: float = 5.6  # M4 x 8 heat-set insert in the tub
    rim_screw_inset: float = 5.0  # from the flange's outer edge
    # On the pier: ears above and below the body, all screws outside the sealed volume
    ear_length: float = 31.0  # past the body, so the screw heads clear the rim flange
    ear_hole_from_tip: float = 9.0
    ear_thickness: float = 6.0
    ear_width: float = 76.0  # stays on the 80 mm pier face
    ear_hole_dia: float = 6.5  # M6 x 70 stainless coach screw
    ear_hole_spacing: float = 60.0
    standoff_from_wood: float = 8.0  # air gap so the wood can dry behind the box
    # PCB and battery inside
    pcb_standoff: float = 10.0
    pcb_standoff_dia: float = 9.0
    pcb_insert_dia: float = 4.2  # M3 x 5 heat-set insert
    pcb_top_clearance: float = 4.0  # top of the PCB to the inner top wall
    battery_bottom_clearance: float = 14.0  # room for the glands' inner nuts
    battery_side_clearance: float = 5.0
    tray_thickness: float = 1.0  # folded galvanised steel pan under the pack
    wire_gap: float = 16.0  # between the pack and the bottom of the PCB
    # Bottom-face openings
    gland_m16_dia: float = 16.2
    gland_m12_dia: float = 12.2
    # Rain hood: its own part, with a real gap so sun does not reach the lid
    hood_overhang_front: float = 24.0
    hood_overhang_side: float = 8.0
    hood_gap: float = 6.0
    hood_thickness: float = 3.0
    hood_slope_deg: float = 8.0
    mass_estimate_kg: float = 0.45  # ASA body plus hood at 40 % infill


@dataclass(frozen=True)
class Printer:
    bed: float = 256.0  # BambuStudio is installed; the 3MF targets a 256 mm bed


SITE = Site()
ROTOR = Rotor()
BRACKET = OriginalBracket()
LAYOUT = Layout()
DRIVE = DriveTrain()
GENERATOR = Generator()
CHARGER = Charger()
PROTECTION = Protection()
BATTERY = Battery()
BOARD = Board()
ENCLOSURE = Enclosure()
PRINTER = Printer()


# --- derived values ------------------------------------------------------------------------------


def rotor_height() -> float:
    """Underside of the bottom section to the top of the cap."""
    return ROTOR.top_centre_z + ROTOR.top_height / 2


def swept_height() -> float:
    """Height of the blades that catch wind: the sections, without the cap's overhang."""
    return ROTOR.section_pitch * (ROTOR.middle_sections + 1)


def swept_area_m2() -> float:
    return ROTOR.diameter * swept_height() * 1e-6


def rotor_mass_kg() -> float:
    return ROTOR.mass_bottom_kg + ROTOR.middle_sections * ROTOR.mass_middle_kg + ROTOR.mass_top_kg


def section_rotation_deg(index: int) -> float:
    """Rotation of middle section `index` (0-based) about z, so the helix runs on unbroken.

    The middle mesh is modelled in the position of index 0.
    """
    return index * ROTOR.section_pitch * ROTOR.twist_deg_per_mm


def rotor_axis_y() -> float:
    """World y of the rotor axis: the plate is on the -y face of the pier."""
    return -(SITE.pier_width / 2 + BRACKET.axis_to_plate)


def rotor_tip_clearance() -> float:
    """Rotor tip to the pier face."""
    return BRACKET.axis_to_plate - ROTOR.diameter / 2


def top_bracket_top_above_rotor() -> float:
    """From the rotor underside to the top of the upper bracket's plate."""
    return rotor_height() + BRACKET.gap_to_rotor + BRACKET.plate_height


def rotor_bottom_z() -> float:
    """World z of the rotor underside."""
    return SITE.pier_height - LAYOUT.top_bracket_margin - top_bracket_top_above_rotor()


def rotor_centre_z() -> float:
    return rotor_bottom_z() + rotor_height() / 2


def bearing_housing_height() -> float:
    return DRIVE.bearing_spacing + DRIVE.bearing_width


def battery_v_full() -> float:
    return BATTERY.cells_series * BATTERY.v_full_cell


def battery_v_empty() -> float:
    return BATTERY.cells_series * BATTERY.v_empty_cell


def battery_v_nominal() -> float:
    return BATTERY.cells_series * BATTERY.v_nominal_cell


def battery_ah() -> float:
    return BATTERY.cells_parallel * BATTERY.cell_ah


def battery_wh() -> float:
    return battery_ah() * battery_v_nominal()


def generator_k() -> float:
    """Back-EMF constant, line-line peak, V per rad/s: k = 60 / (2 pi KV)."""
    return 60.0 / (2 * pi * GENERATOR.kv_rpm_per_v)


def enclosure_outer_width() -> float:
    return ENCLOSURE.inner_width + 2 * ENCLOSURE.wall


def enclosure_outer_height() -> float:
    return ENCLOSURE.inner_height + 2 * ENCLOSURE.wall


def enclosure_tub_depth() -> float:
    """Back face of the tub to the rim."""
    return ENCLOSURE.tub_inner_depth + ENCLOSURE.wall


def enclosure_lid_depth() -> float:
    return ENCLOSURE.lid_inner_depth + ENCLOSURE.wall


def enclosure_flange_width() -> float:
    return enclosure_outer_width() + 2 * ENCLOSURE.flange


def enclosure_flange_height() -> float:
    return enclosure_outer_height() + 2 * ENCLOSURE.flange


def enclosure_total_height() -> float:
    """Top ear to bottom ear: what the longest printed piece needs on the bed."""
    return enclosure_outer_height() + 2 * ENCLOSURE.ear_length
