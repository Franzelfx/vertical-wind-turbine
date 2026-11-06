"""Builds all CAD with freecadcmd: parts, assembly, checks and everything the renderer needs.

    tools/build-cad.sh

Writes to build/cad/: one STEP and STL per printed part, wind-turbine.FCStd (the whole assembly) and
report.json (dimensions and clearance checks, read by tests/test_cad.py). Writes to build/render/:
one STL per item in world coordinates, plus scenes.json.
Generated files: change `spec.py` or the scripts in this folder, never the output.
"""

import hashlib
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(os.environ["VAWT_ROOT"])
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "cad" / "freecad")]

import drivetrain as dt  # noqa: E402
import enclosure as en  # noqa: E402
import FreeCAD as App  # noqa: E402
import Import  # noqa: E402
import Mesh  # noqa: E402
import MeshPart  # noqa: E402
import Part  # noqa: E402
from shapes import box, cyl_x, cyl_y, cyl_z, fuse, tube_along  # noqa: E402

from vawt import spec  # noqa: E402
from vawt.spec import BOARD, BRACKET, ENCLOSURE, LAYOUT, PRINTER, ROTOR, SITE  # noqa: E402

BUILD = ROOT / "build" / "cad"
RENDER = ROOT / "build" / "render"
VENDOR = ROOT / "build" / "vendor"
BOARD_STEP = ROOT / "build" / "kicad" / "charge-board.step"
V = App.Vector


def rotor_to_world():
    return App.Placement(V(0, spec.rotor_axis_y(), spec.rotor_bottom_z()), App.Rotation())


def enclosure_to_world():
    y = SITE.pier_width / 2 + ENCLOSURE.standoff_from_wood
    z = LAYOUT.enclosure_centre_z - spec.enclosure_outer_height() / 2
    return App.Placement(V(0, y, z), App.Rotation())


def moved(shape, placement):
    copy = shape.copy()
    copy.Placement = placement.multiply(copy.Placement)
    return copy


# --- site ----------------------------------------------------------------------------------------


def pier():
    w = SITE.pier_width / 2
    post = box(-w, w, -w, w, 0, SITE.pier_height)
    return post.makeChamfer(1.5, post.Edges)


def pier_sleeve():
    """Steel ground socket for an 80 x 80 post. Only the part above ground is drawn."""
    w = SITE.pier_width / 2
    sleeve = box(-w - 2, w + 2, -w - 2, w + 2, -60, 170).cut(box(-w, w, -w, w, -61, 171))
    bolts = [cyl_x(5, -w - 8, w + 8, 0, z) for z in (40, 130)]
    bolts += [cyl_x(9, -w - 6, -w - 2, 0, z) for z in (40, 130)]
    bolts += [cyl_x(9, w + 2, w + 6, 0, z) for z in (40, 130)]
    return fuse([sleeve, *bolts])


def cable_points():
    """Generator cover to the enclosure's generator gland, clipped along the +x face of the pier."""
    r = rotor_to_world().Base
    e = enclosure_to_world().Base
    _, gx, gy, _ = en.opening("generator_gland")
    start_z = r.z + dt.cover_bottom()
    w = SITE.pier_width / 2 + LAYOUT.cable_conduit_dia / 2 + 1
    gland_y = e.y + gy
    gland_z = e.z - 22
    return [
        (0, r.y - 14, start_z),
        (0, r.y - 14, start_z - 70),
        (w - 8, -70, start_z - 200),
        (w, -8, start_z - 300),
        (w, 0, start_z - 420),
        (w, 0, (start_z + gland_z) / 2),
        (w, 0, gland_z - 160),
        (w + 2, gland_y * 0.45, gland_z - 95),
        (gx, gland_y, gland_z - 40),
        (gx, gland_y, gland_z),
    ]


def cable_clips():
    w = SITE.pier_width / 2
    clips = []
    r = LAYOUT.cable_conduit_dia / 2
    first = rotor_to_world().Base.z + dt.cover_bottom() - 420
    last = enclosure_to_world().Base.z - 150
    for i in range(5):
        z = first + (last - first) * i / 4
        clip = box(w, w + 2, -14, 14, z - 7, z + 7)
        saddle = cyl_z(r + 1.5, z - 7, z + 7, w + r + 1, 0).cut(
            cyl_z(r, z - 8, z + 8, w + r + 1, 0)
        )
        saddle = saddle.common(box(w + 1, w + 2 * r + 4, -r - 2, r + 2, z - 8, z + 8))
        clips.append(clip.fuse(saddle))
    return clips


def board_placement():
    """kicad-cli's STEP frame: x right, y up, z out of the top; origin at the board's centre.

    The board stands with its top towards the lid (+y) and its upper edge up, so a viewer in front
    sees x run the other way: board x -> -x, board y -> +z, board z -> +y.
    """
    x0, x1, z0, z1 = en.pcb_box()
    centre = V((x0 + x1) / 2, en.pcb_y() + BOARD.thickness, (z0 + z1) / 2)
    matrix = App.Matrix(-1, 0, 0, centre.x, 0, 0, 1, centre.y, 0, 1, 0, centre.z, 0, 0, 0, 1)
    return App.Placement(matrix)


def _matrix_rows(placement):
    m = placement.toMatrix()
    return [
        [m.A11, m.A12, m.A13, m.A14],
        [m.A21, m.A22, m.A23, m.A24],
        [m.A31, m.A32, m.A33, m.A34],
        [m.A41, m.A42, m.A43, m.A44],
    ]


def board_placeholder():
    """The board's bare outline, used when no KiCad STEP has been exported yet."""
    x0, x1, z0, z1 = en.pcb_box()
    y = en.pcb_y()
    return box(x0, x1, y, y + BOARD.thickness, z0, z1)


# --- mesh handling -------------------------------------------------------------------------------


def write_mesh(mesh, name):
    RENDER.mkdir(parents=True, exist_ok=True)
    path = RENDER / f"{name}.stl"
    mesh.write(str(path))
    return path.name


def shape_mesh(shape, fine=False):
    # Coarse enough for fast rendering; curved edges stay smooth through Blender's shading
    return MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=0.05 if fine else 0.12,
        AngularDeflection=0.25 if fine else 0.4,
        Relative=False,
    )


def read_vendor(name):
    return Mesh.Mesh(str(VENDOR / f"{name}.stl"))


def placed(mesh, placement):
    copy = mesh.copy()
    copy.Placement = placement
    return copy


def rotor_placements():
    """Each mesh in the rotor frame. Offsets are the 3MF's source offsets."""
    r = rotor_to_world().Base
    items = []
    z = ROTOR.section_height / 2
    base = App.Placement(V(r.x, r.y, r.z + z), App.Rotation())
    items.append(("rotor_bottom", "rotor_bottom", base, "rotor"))
    offset = V(0.093975, -0.025242, 0)
    for i in range(ROTOR.middle_sections):
        z_c = ROTOR.section_height / 2 + (i + 1) * ROTOR.section_pitch
        angle = spec.section_rotation_deg(i)
        rotation = App.Rotation(V(0, 0, 1), angle)
        place = App.Placement(V(r.x, r.y, r.z + z_c) + rotation.multVec(offset), rotation)
        look = "rotor_alt" if i % 2 == 0 else "rotor"
        items.append((f"rotor_middle_{i + 1}", "rotor_middle", place, look))
    top = App.Placement(V(r.x + 0.169609, r.y + 0.171227, r.z + ROTOR.top_centre_z), App.Rotation())
    items.append(("rotor_top", "rotor_top", top, "rotor_alt"))
    return items


def upper_bracket_placement():
    """Mesh frame: plate at +x, hub at -60. Flip so the hub is below the plate, plate to +y."""
    r = rotor_to_world().Base
    flip = App.Rotation(V(1, 0, 0), 180)
    turn = App.Rotation(V(0, 0, 1), 90)
    z = spec.rotor_height() + BRACKET.gap_to_rotor + BRACKET.plate_height / 2
    origin = V(r.x, r.y + 60.0, r.z + z)
    return App.Placement(origin, turn.multiply(flip))


# --- checks --------------------------------------------------------------------------------------


def overlap(a, b):
    return a.common(b).Volume


def overhang_area(mesh, up, limit_deg=46.0):
    """Area leaning further than the limit from vertical, facing down, off the bed: what a printer
    would have to bridge. 46 rather than 45: the tapers are exactly 45 degrees, which prints fine.
    """
    up = V(up.x, up.y, up.z)
    up.normalize()
    heights = [p.x * up.x + p.y * up.y + p.z * up.z for p in mesh.Points]
    bed = min(heights)
    threshold = -math.sin(math.radians(limit_deg))
    total = 0.0
    for facet in mesh.Facets:
        n = facet.Normal
        if n.x * up.x + n.y * up.y + n.z * up.z >= threshold:
            continue
        low = min(p[0] * up.x + p[1] * up.y + p[2] * up.z for p in facet.Points)
        if low > bed + 0.2:
            total += facet.Area
    return total


def check_all(items, seeded):
    report = {}
    for name, (a, b) in items.items():
        report[name] = round(overlap(a, b), 3)
    report["seeded_overlap_must_be_positive"] = round(overlap(*seeded), 3)
    return report


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    rw = rotor_to_world()
    ew = enclosure_to_world()

    # Printed parts, in their own frames. These are the parts you make.
    hood_tilt = math.radians(ENCLOSURE.hood_slope_deg)
    print_parts = {
        # shape, material, count, up vector while printing, how it lies on the bed, supports needed
        "tub": (en.tub(), "ASA", 1, V(0, 1, 0), "back on the bed, opening up", False),
        "lid": (en.lid(), "ASA", 1, V(0, -1, 0), "front on the bed, opening up", False),
        "rain_hood": (
            en.hood(),
            "ASA",
            1,
            V(0, -math.sin(hood_tilt), -math.cos(hood_tilt)),
            "roof on the bed",
            False,
        ),
        "standoff": (en.standoff(), "ASA", 4, V(0, 1, 0), "flat", False),
        "drive_flange": (dt.flange(), "ASA", 1, V(0, 0, 1), "skirt on the bed, boss up", True),
        "drive_bracket": (
            dt.bracket(),
            "ASA",
            1,
            V(0, 0, -1),
            "top flange on the bed: layers run along the arm, its strong way",
            True,
        ),
        "motor_plate": (dt.motor_plate(), "ASA", 1, V(0, 0, 1), "flat", False),
        "generator_cover": (dt.cover(), "ASA", 1, V(0, 0, 1), "floor on the bed", False),
        "coupling": (dt.coupling(), "TPU 95A", 1, V(0, 0, 1), "pins up", True),
    }
    report = {"parts": {}, "checks": {}}
    for name, (shape, material, count, up, lying, supports) in print_parts.items():
        Part.export([_as_object(name, shape)], str(BUILD / f"{name}.step"))
        mesh = shape_mesh(shape, fine=True)
        mesh.write(str(BUILD / f"{name}.stl"))
        bb = shape.BoundBox
        report["parts"][name] = {
            "material": material,
            "count": count,
            "lying": lying,
            "supports": supports,
            "overhang_mm2": round(overhang_area(mesh, up), 0),
            "size_mm": sorted(round(s, 1) for s in (bb.XLength, bb.YLength, bb.ZLength)),
            "volume_cm3": round(shape.Volume / 1000, 1),
            "valid": shape.isValid(),
            "solids": len(shape.Solids),
        }

    # Everything in world coordinates, with a render look. Name -> (shape or mesh, look).
    solids = {
        "pier": (pier(), "wood"),
        "pier_sleeve": (pier_sleeve(), "steel_galv"),
        "tub": (moved(en.tub(), ew), "enclosure"),
        "lid": (moved(en.lid(), ew), "enclosure"),
        "gasket": (moved(en.gasket(), ew), "rubber"),
        "rain_hood": (moved(en.hood(), ew), "enclosure_dark"),
        "battery": (moved(en.battery(), ew), "battery"),
        "tray": (moved(en.tray(), ew), "steel_galv"),
        "strap": (moved(en.strap(), ew), "rubber"),
        "brake_resistor": (moved(en.resistor(), ew), "aluminium"),
        "flange": (moved(dt.flange(), rw), "printed_dark"),
        "bracket_drive": (moved(dt.bracket(), rw), "printed_dark"),
        "motor_plate": (moved(dt.motor_plate(), rw), "printed_dark"),
        "generator_cover": (moved(dt.cover(), rw), "printed_dark"),
        "coupling": (moved(dt.coupling(), rw), "tpu"),
        "rod": (moved(dt.rod(), rw), "steel"),
        "bell": (moved(dt.generator_bell(), rw), "motor"),
        "stator": (moved(dt.generator_stator(), rw), "aluminium"),
        "stub": (moved(dt.upper_stub(), rw), "steel"),
    }
    for i, shape in enumerate(en.standoffs()):
        solids[f"standoff_{i}"] = (moved(shape, ew), "enclosure_dark")
    for i, shape in enumerate(dt.bearings()):
        solids[f"bearing_{i}"] = (moved(shape, rw), "steel")
    for i, shape in enumerate(dt.nuts()):
        solids[f"nut_{i}"] = (moved(shape, rw), "steel")
    for i, shape in enumerate(dt.plate_screws()):
        solids[f"coach_screw_{i}"] = (moved(shape, rw), "steel")
    outer, nuts = en.gland_parts()
    for i, shape in enumerate(outer):
        solids[f"gland_{i}"] = (moved(shape, ew), "black")
    for i, shape in enumerate(nuts):
        solids[f"gland_nut_{i}"] = (moved(shape, ew), "black")
    for i, shape in enumerate(en.rim_screw_parts()):
        solids[f"rim_screw_{i}"] = (moved(shape, ew), "steel")
    for i, (x, z) in enumerate(en.ear_holes()):
        head = cyl_y(7.0, ENCLOSURE.ear_thickness, ENCLOSURE.ear_thickness + 5, x, z)
        if z > spec.enclosure_outer_height():
            head = cyl_y(
                7.0,
                ENCLOSURE.ear_thickness + ENCLOSURE.hood_thickness,
                ENCLOSURE.ear_thickness + ENCLOSURE.hood_thickness + 5,
                x,
                z,
            )
        solids[f"pier_screw_{i}"] = (moved(head, ew), "steel")
    for i, shape in enumerate(cable_clips()):
        solids[f"cable_clip_{i}"] = (shape, "steel_galv")
    solids["cable"] = (tube_along(cable_points(), LAYOUT.cable_conduit_dia / 2), "black")
    wire_shapes = []
    for i, (look, points) in enumerate(en.wires()):
        shape = moved(tube_along(points, 1.1), ew)
        solids[f"wire_{i}"] = (shape, look)
        wire_shapes.append(shape)

    # Upper bracket's coach screws, on the mesh's 40 x 40 pattern
    upper_z = (
        spec.rotor_bottom_z()
        + spec.rotor_height()
        + BRACKET.gap_to_rotor
        + (BRACKET.plate_height / 2)
    )
    plate_y = -SITE.pier_width / 2 - BRACKET.plate_thickness
    for i, (sx, sz) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        x = sx * BRACKET.hole_pattern / 2
        z = upper_z + sz * BRACKET.hole_pattern / 2
        solids[f"upper_screw_{i}"] = (
            fuse(
                [
                    cyl_y(4.0, plate_y - 8, plate_y + 45, x, z),
                    cyl_y(7.5, plate_y - 6, plate_y, x, z),
                ]
            ),
            "steel",
        )

    board = None
    if BOARD_STEP.exists():
        shape = Part.Shape()
        shape.read(str(BOARD_STEP))
        board = moved(shape, ew.multiply(board_placement()))
        solids["board"] = (board, "pcb")
        (RENDER / "board_matrix.json").write_text(
            json.dumps(_matrix_rows(ew.multiply(board_placement()))) + "\n"
        )
    else:
        solids["board"] = (moved(board_placeholder(), ew), "pcb")

    # Check-of-check: a box known to sit in the tub's wall must be seen by the same function
    seeded_box = moved(box(-5, 5, 0.5, 2.5, 50, 60), ew)
    pairs = {
        "battery_vs_tub": (solids["battery"][0], solids["tub"][0]),
        "battery_vs_lid": (solids["battery"][0], solids["lid"][0]),
        "battery_vs_board": (solids["battery"][0], solids["board"][0]),
        "tray_vs_tub": (solids["tray"][0], solids["tub"][0]),
        "board_vs_lid": (solids["board"][0], solids["lid"][0]),
        "board_vs_tub": (solids["board"][0], solids["tub"][0]),
        "resistor_vs_tray": (solids["brake_resistor"][0], solids["tray"][0]),
        "resistor_vs_board": (solids["brake_resistor"][0], solids["board"][0]),
        "lid_vs_tub": (solids["lid"][0], solids["tub"][0]),
        "hood_vs_tub": (solids["rain_hood"][0], solids["tub"][0]),
        "hood_vs_lid": (solids["rain_hood"][0], solids["lid"][0]),
        "tub_vs_pier": (solids["tub"][0], solids["pier"][0]),
        "drive_bracket_vs_pier": (solids["bracket_drive"][0], solids["pier"][0]),
        "cover_vs_bracket": (solids["generator_cover"][0], solids["bracket_drive"][0]),
        "bell_vs_bracket": (solids["bell"][0], solids["bracket_drive"][0]),
        "coupling_vs_bracket": (solids["coupling"][0], solids["bracket_drive"][0]),
        "flange_vs_bracket": (solids["flange"][0], solids["bracket_drive"][0]),
        "motor_plate_vs_bracket": (solids["motor_plate"][0], solids["bracket_drive"][0]),
    }
    for i, wire in enumerate(wire_shapes):
        for other, item in (("lid", "lid"), ("tub", "tub"), ("resistor", "brake_resistor")):
            pairs[f"wire_{i}_vs_{other}"] = (wire, solids[item][0])
    for i, nut in enumerate(nuts):
        for other, item in (
            ("battery", "battery"),
            ("tray", "tray"),
            ("resistor", "brake_resistor"),
        ):
            pairs[f"gland_nut_{i}_vs_{other}"] = (moved(nut, ew), solids[item][0])
    report["checks"] = check_all(pairs, (seeded_box, solids["tub"][0]))

    board_bb = solids["board"][0].BoundBox
    report["board"] = {
        "real_geometry": BOARD_STEP.exists(),
        "x": [round(board_bb.XMin - ew.Base.x, 2), round(board_bb.XMax - ew.Base.x, 2)],
        "y_top_local": round(board_bb.YMax - ew.Base.y, 2),
        "z": [round(board_bb.ZMin - ew.Base.z, 2), round(board_bb.ZMax - ew.Base.z, 2)],
    }

    # Volume taken by the printed flange's bolts must not break out into the bore or the seat
    report["flange_bolt_margin_mm"] = {
        "to_seat": round(
            spec.DRIVE.flange_bolt_pcd / 2
            - spec.DRIVE.flange_bolt_dia / 2
            - ROTOR.bearing_seat_dia / 2,
            2,
        ),
    }

    # Rotor from the meshes
    meshes = {}
    rotor_low = [math.inf] * 3
    rotor_high = [-math.inf] * 3
    max_radius = 0.0
    rotor_y = spec.rotor_axis_y()
    vendored = (VENDOR / "rotor_bottom.stl").exists()
    if vendored:
        cache = {
            n: read_vendor(n) for n in ("rotor_bottom", "rotor_middle", "rotor_top", "bracket")
        }
        for name, source, place, look in rotor_placements():
            mesh = placed(cache[source], place)
            meshes[name] = (mesh, look)
            # From the points: a placed mesh's BoundBox is the rotated local box, far too large
            for p in mesh.Points:
                rotor_low = [min(rotor_low[0], p.x), min(rotor_low[1], p.y), min(rotor_low[2], p.z)]
                rotor_high = [
                    max(rotor_high[0], p.x),
                    max(rotor_high[1], p.y),
                    max(rotor_high[2], p.z),
                ]
                max_radius = max(max_radius, math.hypot(p.x, p.y - rotor_y))
        meshes["bracket_top"] = (
            placed(cache["bracket"], upper_bracket_placement()),
            "printed_dark",
        )
        bb = meshes["bracket_top"][0].BoundBox
        report["bracket_top"] = {
            "y_max": round(bb.YMax, 2),
            "z_min": round(bb.ZMin, 2),
            "z_max": round(bb.ZMax, 2),
        }
        report["rotor"] = {
            "z_min": round(rotor_low[2], 2),
            "z_max": round(rotor_high[2], 2),
            "max_radius": round(max_radius, 2),
            "tip_y_max": round(rotor_high[1], 2),
        }
    report["vendored"] = vendored

    # Fingerprint: stale reports fail in tests/test_cad.py
    h = hashlib.sha256()
    for path in [ROOT / "src/vawt/spec.py", *sorted((ROOT / "cad/freecad").glob("*.py"))]:
        h.update(path.read_bytes())
    report["fingerprint"] = h.hexdigest()
    report["enclosure"] = {
        "longest_part_mm": max(max(report["parts"][n]["size_mm"]) for n in report["parts"]),
        "bed_mm": PRINTER.bed,
    }
    report["cable_length_m"] = round(Part.Wire(_curve(cable_points()).toShape()).Length / 1000, 2)
    (BUILD / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "docs" / "printing.md").write_text(printing_page(report))

    # Render scenes: one STL per item, then lists of what appears in each scene
    print("meshes for rendering ...", flush=True)
    manifest = {}
    for name, (shape, look) in solids.items():
        manifest[name] = {"file": write_mesh(shape_mesh(shape), name), "material": look}
    for name, (mesh, look) in meshes.items():
        manifest[name] = {"file": write_mesh(mesh, name), "material": look}
    (RENDER / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (RENDER / "layout.json").write_text(
        json.dumps(
            {
                "rotor_axis": [0.0, spec.rotor_axis_y(), spec.rotor_bottom_z()],
                "rotor_height": spec.rotor_height(),
                "enclosure_origin": [ew.Base.x, ew.Base.y, ew.Base.z],
                "enclosure_size": [
                    spec.enclosure_flange_width(),
                    spec.enclosure_tub_depth() + spec.enclosure_lid_depth(),
                    spec.enclosure_outer_height(),
                ],
                "pier_height": SITE.pier_height,
                "generator_z": spec.rotor_bottom_z() + dt.bell_top(),
            },
            indent=2,
        )
        + "\n"
    )

    # The FreeCAD document: every item as a named object, grouped
    print("writing the FreeCAD document ...", flush=True)
    doc = App.newDocument("wind_turbine")
    groups = {}
    for name, (shape, _look) in solids.items():
        group = _group_for(name)
        groups.setdefault(group, []).append(_add_shape(doc, name, shape))
    for name, (mesh, _look) in meshes.items():
        obj = doc.addObject("Mesh::Feature", name)
        obj.Mesh = mesh
        groups.setdefault("Rotor (licensed meshes)", []).append(obj)
    for label, members in groups.items():
        group = doc.addObject(
            "App::DocumentObjectGroup", label.replace(" ", "_").replace("(", "").replace(")", "")
        )
        group.Label = label
        group.addObjects(members)
    doc.recompute()
    doc.saveAs(str(BUILD / "wind-turbine.FCStd"))
    print("wrote", BUILD / "wind-turbine.FCStd")
    colour_list = {name: look for name, (_, look) in {**solids, **meshes}.items()}
    (BUILD / "colours.json").write_text(json.dumps(colour_list, indent=2) + "\n")


def printing_page(report):
    rows = [
        "| Part | Qty | Material | How it lies | Size (mm) | Volume (cm3) | Supports |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, part in report["parts"].items():
        size = " x ".join(f"{v:.0f}" for v in reversed(part["size_mm"]))
        needed = f"yes, {part['overhang_mm2']:.0f} mm2" if part["supports"] else "no"
        rows.append(
            f"| `{name}` | {part['count']} | {part['material']} | {part['lying']} | {size} "
            f"| {part['volume_cm3']} | {needed} |"
        )
    table = "\n".join(rows)
    return f"""# Printing

> Generated by `tools/build-cad.sh` from `cad/freecad/build.py`; do not edit by hand
> (`tests/test_cad.py` fails when this page and the build drift apart).

For this project's own parts. STEP and STL land in `build/cad/`. All fit a {PRINTER.bed:.0f} mm bed.

{table}

The check counts surfaces leaning more than 46 degrees from vertical, facing down, off the bed. Parts marked "no" have
only short bridges: hole tops, the gasket groove, the lid's 1 mm ledge. Print enclosure parts with at
least 4 perimeters, for sealing (ADR-008). Rotor printing: `docs/hardware.md`.
"""


def _curve(points):
    curve = Part.BSplineCurve()
    curve.interpolate([V(*p) for p in points])
    return curve


def _as_object(name, shape):
    doc = App.ActiveDocument or App.newDocument("export")
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def _add_shape(doc, name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def _group_for(name):
    if name in ("pier", "pier_sleeve") or name.startswith(("upper_screw", "cable", "coach")):
        return "Site"
    if name.startswith(
        (
            "tub",
            "lid",
            "gasket",
            "rain_hood",
            "battery",
            "tray",
            "strap",
            "brake",
            "board",
            "gland",
            "rim_screw",
            "pier_screw",
            "wire",
        )
    ):
        return "Enclosure"
    return "Drive train"


main()
_ = Import  # imported for its STEP registration side effects in some FreeCAD builds
