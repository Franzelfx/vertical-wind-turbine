"""The electronics enclosure: tub, lid, rain hood and gasket, from `vawt.spec`.

Local frame: x across (centred), z up from the outer underside of the tub, y from the tub's back
face towards the lid. +y points away from the pier.
"""

from shapes import box, cut, cyl_y, cyl_z, extrude_x, fuse, rounded_loop_y, rounded_prism_y

from vawt import spec
from vawt.spec import BATTERY, BOARD
from vawt.spec import ENCLOSURE as E


def outer_w():
    return spec.enclosure_outer_width()


def outer_h():
    return spec.enclosure_outer_height()


def tub_depth():
    return spec.enclosure_tub_depth()


def lid_depth():
    return spec.enclosure_lid_depth()


def centre_z():
    return outer_h() / 2


def inner_z0():
    return E.wall


def inner_z1():
    return E.wall + E.inner_height


def rim_screws():
    """(x, z) of the six rim screws: corners and the middle of the long sides."""
    x = outer_w() / 2 + E.flange - E.rim_screw_inset
    dz = outer_h() / 2 + E.flange - E.rim_screw_inset
    return [(s * x, centre_z() + t * dz) for s in (-1, 1) for t in (-1, 0, 1)]


def ear_holes():
    """(x, z) of the four coach screws into the pier."""
    z_low = -(E.ear_length - E.ear_hole_from_tip)
    z_high = outer_h() + E.ear_length - E.ear_hole_from_tip
    return [(s * E.ear_hole_spacing / 2, z) for s in (-1, 1) for z in (z_low, z_high)]


def pcb_box():
    """(x0, x1, z0, z1) of the board inside the box."""
    z1 = inner_z1() - E.pcb_top_clearance
    return -BOARD.width / 2, BOARD.width / 2, z1 - BOARD.height, z1


def pcb_y():
    """Back face of the board."""
    return E.wall + E.pcb_standoff


def pcb_holes():
    x0, x1, z0, z1 = pcb_box()
    i = BOARD.hole_inset
    return [(x, z) for x in (x0 + i, x1 - i) for z in (z0 + i, z1 - i)]


def battery_box():
    """(x0, x1, y0, y1, z0, z1) of the pack, on its steel tray in the lower left of the box."""
    x0 = -E.inner_width / 2 + E.battery_side_clearance + E.tray_thickness
    z0 = inner_z0() + E.battery_bottom_clearance + E.tray_thickness
    y0 = E.wall + E.tray_thickness
    return x0, x0 + BATTERY.length, y0, y0 + BATTERY.depth, z0, z0 + BATTERY.height


def openings():
    """Bottom-face openings: (name, x, y, diameter). Cables and vent only ever leave downwards."""
    y = (E.wall + (tub_depth() - E.flange_thickness)) / 2
    return [
        ("load_gland", -42.0, y, E.gland_m16_dia),
        ("vent", -14.0, y, E.gland_m12_dia),
        ("brake_switch", 14.0, y, E.gland_m12_dia),
        ("generator_gland", 40.0, y, E.gland_m16_dia),
    ]


def opening(name):
    return next(o for o in openings() if o[0] == name)


def terminal_x(name):
    """Local x of a terminal block on the board: board x is mirrored, see ADR-007."""
    return -dict(BOARD.terminals)[name]


def wires():
    """Looks of the wiring, routed with real clearances: (look, points) in the box's frame."""
    z_terminal = pcb_box()[2] - 0.5
    y_terminal = pcb_y() + BOARD.thickness + 5.0
    bx0, bx1, _, by1, bz0, bz1 = battery_box()
    run = []
    _, gx, gy, _ = opening("generator_gland")
    for i, (look, dx) in enumerate(
        (("wire_red", -5.08), ("wire_yellow", 0.0), ("wire_blue", 5.08))
    ):
        tx = terminal_x("GENERATOR") + dx
        run.append(
            (
                look,
                [
                    (gx + (i - 1) * 3.0, gy, E.wall + 6.0),
                    (gx + (i - 1) * 3.0, gy + 2, 34.0),
                    (tx, gy + 8, 70.0),
                    (tx, y_terminal, z_terminal),
                ],
            )
        )
    _, lx, ly, _ = opening("load_gland")
    for look, dx in (("wire_red", -2.54), ("wire_black", 2.54)):
        tx = terminal_x("LOAD") + dx
        front = by1 + 3.5
        run.append(
            (
                look,
                [
                    (lx + dx, ly, E.wall + 6.0),
                    (lx + dx, ly + 12.0, bz0 - 4.0),
                    (lx + dx, front - 1.0, bz0 + 12.0),
                    (lx + dx, front, bz1 - 22.0),
                    (lx + dx + 3.0, front - 1.0, bz1 - 4.0),
                    (tx, y_terminal + 12.0, z_terminal - 8.0),
                    (tx, y_terminal, z_terminal),
                ],
            )
        )
    for look, dx in (("wire_red", -2.54), ("wire_black", 2.54)):
        tx = terminal_x("PACK") + dx
        run.append(
            (
                look,
                [(tx, by1 - 12.0, bz1), (tx, by1 - 12.0, bz1 + 5.0), (tx, y_terminal, z_terminal)],
            )
        )
    tx = terminal_x("PACK_NTC")
    run.append(
        (
            "wire_white",
            [
                (tx + 1.25, by1 - 6.0, bz1),
                (tx + 1.25, by1 - 5.0, bz1 + 4.0),
                (tx + 1.25, y_terminal, z_terminal),
            ],
        )
    )
    # Brake: bus terminal to the switch, switch to resistor, resistor back to ground
    _, sx, sy, _ = opening("brake_switch")
    rx0, rx1, _, ry1, rz0, rz1 = resistor_box()
    tx = terminal_x("BRAKE")
    run.append(
        (
            "wire_red",
            [
                (tx - 2.54, y_terminal, z_terminal),
                (tx - 2.54, ry1 + 13.0, 84.0),
                (sx + 9.0, ry1 + 13.0, 50.0),
                (sx + 2.0, sy + 2.0, E.wall + 8.0),
            ],
        )
    )
    run.append(
        (
            "wire_black",
            [
                (tx + 2.54, y_terminal, z_terminal),
                (rx1 - 8.0, ry1 + 6.0, rz1 + 12.0),
                (rx1 - 3.0, ry1 - 8.0, rz1 + 7.0),
            ],
        )
    )
    return run


def resistor_box():
    """(x0, x1, y0, y1, z0, z1) of the brake resistor, on the tub floor right of the pack."""
    x0 = battery_box()[1] + 6
    return x0, x0 + 30.0, E.wall, E.wall + 16.0, inner_z0() + 26.0, inner_z0() + 26.0 + 30.0


def tub():
    body = rounded_prism_y(outer_w(), outer_h(), 0, tub_depth(), E.corner_radius, 0, centre_z())
    cavity = rounded_prism_y(
        E.inner_width,
        E.inner_height,
        E.wall,
        tub_depth() + 1,
        E.corner_radius - E.wall,
        0,
        centre_z(),
    )
    rim = rounded_prism_y(
        spec.enclosure_flange_width(),
        spec.enclosure_flange_height(),
        tub_depth() - E.flange_thickness,
        tub_depth(),
        E.flange_corner_radius,
        0,
        centre_z(),
    )
    # Back plate with the four ears: reaches past the rim so the screw heads stay reachable
    ears = box(
        -E.ear_width / 2,
        E.ear_width / 2,
        0,
        E.ear_thickness,
        -E.ear_length,
        outer_h() + E.ear_length,
    )
    gussets = []
    for x in (-E.ear_width / 2 + 2, E.ear_width / 2 - 6):
        gussets.append(
            extrude_x(
                [(E.ear_thickness, -E.ear_length + 2), (E.ear_thickness, 0), (24.0, 0)], x, x + 4
            )
        )
        gussets.append(
            extrude_x(
                # Short: the rain hood's tab sits on the upper ear above this
                [
                    (E.ear_thickness, outer_h() + 11.0),
                    (E.ear_thickness, outer_h()),
                    (24.0, outer_h()),
                ],
                x,
                x + 4,
            )
        )
    pads = [cyl_y(9.0, -E.standoff_from_wood, 0, x, z) for x, z in ear_holes()]
    solid = fuse([body, rim, ears, *gussets, *pads]).cut(cavity)
    # What goes back inside the cavity: board posts and resistor lands
    posts = [cyl_y(E.pcb_standoff_dia / 2, E.wall - 0.1, pcb_y(), x, z) for x, z in pcb_holes()]
    x0, x1, _, _, z0, z1 = resistor_box()
    lands = [
        cyl_y(4.5, E.wall - 0.1, E.wall + 3.0, x, z)
        for x in (x0 - 0.0 + 3, x1 - 3)
        for z in (z0 - 5, z1 + 5)
    ]
    ribs = []
    bx0, bx1, _, _, bz0, bz1 = battery_box()
    t = E.tray_thickness
    for z in (bz0 - t - 5, bz1 + 5):  # strap lands above and below the pack's tray
        ribs.append(box(bx0 + 6, bx1 - 6, E.wall - 0.1, E.wall + 3.0, z - 2, z + 2))
    solid = fuse([solid, *posts, *lands, *ribs])
    holes = [cyl_y(E.pcb_insert_dia / 2, E.wall + 2.0, pcb_y() + 1, x, z) for x, z in pcb_holes()]
    holes += [
        cyl_y(E.ear_hole_dia / 2, -E.standoff_from_wood - 1, 10, x, z) for x, z in ear_holes()
    ]
    # Rim: gasket groove and heat-set inserts, opened from the rim's face
    centre_w = outer_w() + 2 * E.gasket_offset
    centre_h = outer_h() + 2 * E.gasket_offset
    groove = rounded_loop_y(
        centre_w,
        centre_h,
        tub_depth() - E.gasket_groove_depth,
        tub_depth() + 1,
        E.corner_radius + E.gasket_offset,
        E.gasket_groove_width,
    ).translated((0, 0, centre_z()))
    holes.append(groove)
    holes += [
        cyl_y(E.rim_insert_dia / 2, tub_depth() - 8, tub_depth() + 1, x, z) for x, z in rim_screws()
    ]
    # Rim bosses keep the insert pockets in solid material behind the flange
    bosses = [
        cyl_y(5.0, tub_depth() - 10, tub_depth() - E.flange_thickness + 0.1, x, z)
        for x, z in rim_screws()
    ]
    solid = fuse([solid, *bosses])
    for _, x, y, dia in openings():
        holes.append(cyl_z(dia / 2, -1, E.wall + 1, x, y))
    return cut(solid, holes)


def lid():
    y0 = tub_depth()
    y1 = y0 + lid_depth()
    body = rounded_prism_y(outer_w(), outer_h(), y0, y1, E.corner_radius, 0, centre_z())
    rim = rounded_prism_y(
        spec.enclosure_flange_width(),
        spec.enclosure_flange_height(),
        y0,
        y0 + E.flange_thickness,
        E.flange_corner_radius,
        0,
        centre_z(),
    )
    cavity = rounded_prism_y(
        E.inner_width,
        E.inner_height,
        y0 - 1,
        y0 + E.lid_inner_depth,
        E.corner_radius - E.wall,
        0,
        centre_z(),
    )
    label = rounded_prism_y(70, 40, y1 - 0.6, y1 + 1, 2, 0, centre_z() + 30)
    solid = fuse([body, rim]).cut(cavity).cut(label)
    holes = []
    for x, z in rim_screws():
        holes.append(cyl_y(E.rim_screw_dia / 2, y0 - 1, y0 + E.flange_thickness + 1, x, z))
        holes.append(cyl_y(4.2, y0 + E.flange_thickness - 2, y0 + E.flange_thickness + 1, x, z))
    return cut(solid, holes)


def gasket():
    centre_w = outer_w() + 2 * E.gasket_offset
    centre_h = outer_h() + 2 * E.gasket_offset
    y0 = tub_depth() - E.gasket_groove_depth
    return rounded_loop_y(
        centre_w, centre_h, y0, tub_depth(), E.corner_radius + E.gasket_offset, E.gasket_cord_dia
    ).translated((0, 0, centre_z()))


def hood():
    """Sloped roof with drip lip and side cheeks, held by the upper two coach screws."""
    half = spec.enclosure_flange_width() / 2 + E.hood_overhang_side
    t = E.hood_thickness
    y_rear = E.ear_thickness
    y_front = tub_depth() + lid_depth() + E.hood_overhang_front
    flange_top = outer_h() + E.flange
    import math

    slope = math.tan(math.radians(E.hood_slope_deg))
    hole_z = ear_holes()[1][1]
    z_rear = hole_z + 9.0

    def underside(y):
        return z_rear - (y - y_rear) * slope

    # Clearance is what the rim needs at the point the slope comes closest
    clearance = underside(tub_depth() + E.flange_thickness) - flange_top
    if clearance < E.hood_gap:
        raise ValueError(f"hood gap {clearance:.1f} mm, needs {E.hood_gap}")
    roof = extrude_x(
        [
            (y_rear, z_rear),
            (y_front, underside(y_front)),
            (y_front, underside(y_front) + t),
            (y_rear, z_rear + t),
        ],
        -half,
        half,
    )
    lip = extrude_x(
        [
            (y_front - t, underside(y_front - t)),
            (y_front, underside(y_front)),
            (y_front, underside(y_front) - 10),
            (y_front - t, underside(y_front - t) - 10),
        ],
        -half,
        half,
    )
    cheek_points = [
        (y_rear, z_rear),
        (y_front, underside(y_front)),
        (y_front, underside(y_front) - 10),
        (tub_depth(), flange_top - 2),
        (y_rear, flange_top - 2),
    ]
    cheeks = [extrude_x(cheek_points, x, x + t) for x in (-half, half - t)]
    tab_half = E.ear_width / 2
    tab = box(-tab_half, tab_half, y_rear, y_rear + t, hole_z - 9, z_rear + t)
    solid = fuse([roof, lip, *cheeks, tab])
    screw_holes = [
        cyl_y(E.ear_hole_dia / 2, y_rear - 1, y_rear + t + 1, x, hole_z)
        for x, z in ear_holes()
        if z > outer_h()
    ]
    return cut(solid, screw_holes)


def tray():
    """Folded galvanised steel pan around the pack's back and sides: not printed, for fire."""
    x0, x1, y0, y1, z0, z1 = battery_box()
    t = E.tray_thickness
    pan = box(x0 - t, x1 + t, E.wall, y0 + 16, z0 - t, z1 + t)
    return pan.cut(box(x0, x1, y0, y0 + 20, z0, z1))


def battery():
    x0, x1, y0, y1, z0, z1 = battery_box()
    pack = box(x0, x1, y0, y1, z0, z1)
    return pack.makeFillet(2.0, pack.Edges)


def strap():
    x0, x1, y0, y1, z0, z1 = battery_box()
    m = (x0 + x1) / 2
    band = box(m - 10, m + 10, E.wall, y1 + 1.2, z0 - 7, z1 + 7)
    return band.cut(box(m - 11, m + 11, E.wall - 1, y1, z0 - 5, z1 + 5))


def resistor():
    x0, x1, y0, y1, z0, z1 = resistor_box()
    body = box(x0 + 4, x1 - 4, y0 + 3, y1, z0, z1)
    tabs = box(x0, x1, y0 + 3, y0 + 5, z0 - 8, z1 + 8)
    return fuse([body, tabs])


def gland_parts():
    """Looks of the fittings, with their real space claim inside and outside the box."""
    outer, nuts = [], []
    for name, x, y, dia in openings():
        if name == "brake_switch":
            outer.append(cyl_z(7.5, -8, 0, x, y))
            outer.append(cyl_z(2.5, -22, -8, x, y))
            nuts.append(cyl_z(dia / 2 + 3, E.wall, E.wall + 3, x, y))
        elif name == "vent":
            outer.append(cyl_z(9.0, -9, 0, x, y))
            nuts.append(cyl_z(dia / 2 + 3, E.wall, E.wall + 4, x, y))
        else:
            outer.append(cyl_z(dia / 2 + 3.0, -10, 0, x, y))
            outer.append(cyl_z(dia / 2 - 1.0, -22, -10, x, y))
            nuts.append(cyl_z(dia / 2 + 4.0, E.wall, E.wall + 7, x, y))
    return outer, nuts


def rim_screw_parts():
    y1 = tub_depth() + E.flange_thickness
    return [
        fuse([cyl_y(3.6, y1 - 2.0, y1 + 0.5, x, z), cyl_y(2.0, tub_depth() - 8, y1 - 2, x, z)])
        for x, z in rim_screws()
    ]


__all__ = [
    "opening",
    "wires",
    "battery",
    "battery_box",
    "ear_holes",
    "gasket",
    "gland_parts",
    "hood",
    "lid",
    "openings",
    "pcb_box",
    "pcb_holes",
    "pcb_y",
    "resistor",
    "rim_screw_parts",
    "strap",
    "tray",
    "tub",
]
