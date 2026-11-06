"""The new drive train under the rotor (ADR-004), from `vawt.spec`.

Rotor frame: origin on the axis at the rotor's underside; z up; +y towards the pier.
"""

from shapes import box, cut, cyl_x, cyl_y, cyl_z, extrude_x, fuse, hexagon_z, polar

from vawt import spec
from vawt.spec import BRACKET
from vawt.spec import DRIVE as D
from vawt.spec import GENERATOR as G

NUT_AF = 13.0  # M8 hex nut, across flats
NUT_HEIGHT = 6.5


def housing_top():
    return -(D.flange_thickness + D.housing_top_gap)


def housing_bottom():
    return housing_top() - spec.bearing_housing_height()


def cage_disc_bottom():
    return housing_bottom() - D.cage_plate_thickness


def bell_top():
    return housing_bottom() - D.coupling_length


def motor_bottom():
    return bell_top() - G.height


def motor_plate_bottom():
    return motor_bottom() - D.cage_plate_thickness


def cover_inner_radius():
    return D.cage_pcd / 2 + D.cage_post_dia / 2 + D.cover_clearance


def cover_top():
    return housing_bottom() + 2.0


def cover_bottom():
    return motor_plate_bottom() - 4.0 - D.cover_wall


def plate_y0():
    return BRACKET.axis_to_plate - D.plate_thickness


def plate_centre_z():
    return housing_top() - D.plate_height / 2


def plate_holes():
    return [
        (s * D.plate_hole_pattern_w / 2, plate_centre_z() + t * D.plate_hole_pattern_h / 2)
        for s in (-1, 1)
        for t in (-1, 1)
    ]


def post_positions():
    """Cage posts, leaving the pier side free for the arm."""
    return [polar(D.cage_pcd / 2, a) for a in (30, 150, 270)]


def flange():
    """Replaces the rotor's lower bearing: bolted through the floor, holds the rod with a nut."""
    disc = cyl_z(D.flange_dia / 2, -D.flange_thickness, 0)
    boss = cyl_z(D.flange_boss_dia / 2, 0, spec.ROTOR.bearing_seat_depth - 0.5)
    skirt = cyl_z(
        D.flange_dia / 2, -D.flange_thickness - D.flange_skirt_height, -D.flange_thickness
    )
    skirt = skirt.cut(
        cyl_z(
            D.flange_dia / 2 - 3,
            -D.flange_thickness - D.flange_skirt_height - 1,
            -D.flange_thickness,
        )
    )
    solid = fuse([disc, boss, skirt])
    holes = [cyl_z(D.shaft_dia / 2 + 0.2, -D.flange_thickness - 1, spec.ROTOR.bearing_seat_depth)]
    holes.append(
        hexagon_z(
            NUT_AF + 0.3,
            spec.ROTOR.bearing_seat_depth - 0.5 - NUT_HEIGHT - 0.5,
            spec.ROTOR.bearing_seat_depth,
        )
    )
    for i in range(D.flange_bolts):
        x, y = polar(D.flange_bolt_pcd / 2, 90 + i * 360 / D.flange_bolts)
        holes.append(cyl_z(D.flange_bolt_dia / 2, -D.flange_thickness - 1, 1, x, y))
    x, y = polar(D.lock_pin_pcd / 2, -60)
    holes.append(cyl_z(D.lock_pin_dia / 2, -D.flange_thickness - 1, -0.5, x, y))
    return cut(solid, holes)


def bracket():
    """Bearing housing on the original 140 mm reach, plus the cage's upper disc."""
    top, bottom = housing_top(), housing_bottom()
    housing = cyl_z(D.housing_od / 2, bottom, top)
    disc = cyl_z(D.cage_pcd / 2 + D.cage_post_dia / 2 + 0.5, cage_disc_bottom(), bottom)
    disc = disc.cut(cyl_z(D.coupling_dia / 2 + 2, cage_disc_bottom() - 1, bottom))
    # Arm: flat top flange plus a deep web that rises clear of the generator cover
    plate = box(
        -D.plate_width / 2,
        D.plate_width / 2,
        plate_y0(),
        BRACKET.axis_to_plate,
        plate_centre_z() - D.plate_height / 2,
        plate_centre_z() + D.plate_height / 2,
    )
    flange_top = box(-D.arm_width / 2, D.arm_width / 2, 0, plate_y0() + 0.1, top - 8, top)
    z_low_plate = plate_centre_z() - D.plate_height / 2 + 6
    y_cover = cover_inner_radius() + D.cover_wall + 3
    web = extrude_x(
        [
            (0, top - 1),
            (plate_y0() + 0.1, top - 1),
            (plate_y0() + 0.1, z_low_plate),
            (y_cover, cover_top() + 1),
            (0, cover_top() + 1),
        ],
        -D.arm_rib_thickness / 2,
        D.arm_rib_thickness / 2,
    )
    lug_x, lug_y = polar(D.lock_pin_pcd / 2, -60)
    lug = cyl_z(7.0, top - 8, top, lug_x, lug_y)
    posts = [
        cyl_z(D.cage_post_dia / 2, motor_bottom(), cage_disc_bottom() + 0.1, x, y)
        for x, y in post_positions()
    ]
    solid = fuse([housing, disc, plate, flange_top, web, lug, *posts])
    holes = [
        cyl_z(D.bearing_seat_dia / 2, top - D.bearing_width, top + 1),
        cyl_z(D.bearing_seat_dia / 2, bottom - 1, bottom + D.bearing_width),
        cyl_z(D.shaft_dia / 2 + 2, bottom, top),
        cyl_z(D.lock_pin_dia / 2, top - 9, top + 1, lug_x, lug_y),
    ]
    holes += [
        cyl_y(D.plate_hole_dia / 2, plate_y0() - 1, BRACKET.axis_to_plate + 1, x, z)
        for x, z in plate_holes()
    ]
    holes += [
        cyl_z(1.9, motor_bottom() - 1, motor_bottom() + 10, x, y) for x, y in post_positions()
    ]
    # Two screws hold the cover on the disc from the side
    holes += [
        cyl_x(
            1.6,
            -cover_inner_radius() - 1,
            -cover_inner_radius() + 8,
            0,
            cage_disc_bottom() + D.cage_plate_thickness / 2,
        )
    ]
    holes += [
        cyl_x(
            1.6,
            cover_inner_radius() - 8,
            cover_inner_radius() + 1,
            0,
            cage_disc_bottom() + D.cage_plate_thickness / 2,
        )
    ]
    return cut(solid, holes)


def motor_plate():
    z0, z1 = motor_plate_bottom(), motor_bottom()
    plate = cyl_z(D.cage_pcd / 2 + D.cage_post_dia / 2 + 0.5, z0, z1)
    holes = [cyl_z(2.2, z0 - 1, z1 + 1, x, y) for x, y in post_positions()]
    holes.append(cyl_z(6.5, z0 - 1, z1 + 1))  # hollow shaft and wires
    # ASSUMPTION: M3 on a 25 mm circle; check against the motor on delivery (B1)
    holes += [cyl_z(1.7, z0 - 1, z1 + 1, *polar(12.5, a)) for a in (45, 135, 225, 315)]
    return cut(plate, holes)


def cover():
    """Rain cover over generator and cage. Drains through the floor, cable leaves downwards."""
    r = cover_inner_radius()
    outer = cyl_z(r + D.cover_wall, cover_bottom(), cover_top())
    inner = cyl_z(r, cover_bottom() + D.cover_wall, cover_top() + 1)
    solid = outer.cut(inner)
    holes = [cyl_z(6.1, cover_bottom() - 1, cover_bottom() + D.cover_wall + 1, 0, -14)]
    holes += [
        cyl_z(2.0, cover_bottom() - 1, cover_bottom() + D.cover_wall + 1, *polar(r - 8, a))
        for a in (20, 100, 200, 300)
    ]
    z = cage_disc_bottom() + D.cage_plate_thickness / 2
    holes += [
        cyl_x(2.0, -r - D.cover_wall - 1, -r + 1, 0, z),
        cyl_x(2.0, r - 1, r + D.cover_wall + 1, 0, z),
    ]
    # The arm's web comes in at the top on the pier side
    holes.append(
        box(
            -D.arm_rib_thickness / 2 - 1,
            D.arm_rib_thickness / 2 + 1,
            0,
            r + 6,
            cover_top() - 2,
            cover_top() + 1,
        )
    )
    return cut(solid, holes)


def rod():
    top = spec.ROTOR.bearing_seat_depth - 0.5
    return cyl_z(D.shaft_dia / 2, housing_bottom() - D.coupling_length * 0.6, top)


def bearings():
    t, b = housing_top(), housing_bottom()
    parts = []
    for z0 in (t - D.bearing_width, b):
        ring = cyl_z(D.bearing_od / 2, z0, z0 + D.bearing_width)
        parts.append(ring.cut(cyl_z(D.shaft_dia / 2, z0 - 1, z0 + D.bearing_width + 1)))
    return parts


def nuts():
    top = spec.ROTOR.bearing_seat_depth - 0.5
    locks = [
        hexagon_z(NUT_AF, top - NUT_HEIGHT - 0.5, top - 0.5),
        hexagon_z(NUT_AF, housing_top() + 0.2, housing_top() + NUT_HEIGHT + 0.2),
    ]
    return [n.cut(cyl_z(D.shaft_dia / 2, -1000, 1000)) for n in locks]


def coupling():
    """TPU spider: nut pocket on the rod, two pins into the bell's top holes."""
    z1 = housing_bottom() - 0.5
    z0 = bell_top() + 0.5
    body = cyl_z(D.coupling_dia / 2, z0, z1)
    waist = cyl_z(D.coupling_dia / 2 + 1, z0 + 8, z0 + 12).cut(cyl_z(10, z0 + 7, z0 + 13))
    solid = body.cut(waist)
    return solid.cut(cyl_z(D.shaft_dia / 2, z0 + 14, z1 + 1))


def generator_bell():
    z1 = bell_top()
    return cyl_z(G.diameter / 2, z1 - 24.0, z1)


def generator_stator():
    z1 = bell_top() - 24.0
    return cyl_z(18.0, motor_bottom(), z1)


def upper_stub():
    """M8 bolt held in the original bracket: the rotor's top bearing rides on it."""
    top = spec.rotor_height()
    return cyl_z(4.0, top - 10, top + BRACKET.gap_to_rotor + BRACKET.hub_thickness + 8)


def plate_screws():
    return [
        fuse(
            [
                cyl_y(4.0, plate_y0() - 12, BRACKET.axis_to_plate + 45, x, z),
                cyl_y(7.5, plate_y0() - 6, plate_y0(), x, z),
            ]
        )
        for x, z in plate_holes()
    ]


__all__ = [
    "bearings",
    "bracket",
    "coupling",
    "cover",
    "cover_bottom",
    "flange",
    "generator_bell",
    "generator_stator",
    "motor_plate",
    "nuts",
    "plate_screws",
    "rod",
    "upper_stub",
]
