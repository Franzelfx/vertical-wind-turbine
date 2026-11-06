"""Small geometry helpers on FreeCAD's Part kernel. Runs inside freecadcmd."""

import math

import FreeCAD as App
import Part

V = App.Vector


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_z(radius, z0, z1, x=0.0, y=0.0):
    return Part.makeCylinder(radius, z1 - z0, V(x, y, z0), V(0, 0, 1))


def cyl_y(radius, y0, y1, x=0.0, z=0.0):
    return Part.makeCylinder(radius, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cyl_x(radius, x0, x1, y=0.0, z=0.0):
    return Part.makeCylinder(radius, x1 - x0, V(x0, y, z), V(1, 0, 0))


def rounded_prism_y(width, height, y0, y1, radius, cx=0.0, cz=0.0):
    """A plate along y with rounded corners in the x-z plane, centred on (cx, cz)."""
    solid = box(cx - width / 2, cx + width / 2, y0, y1, cz - height / 2, cz + height / 2)
    if radius <= 0:
        return solid
    edges = [e for e in solid.Edges if abs(e.Vertexes[0].Point.y - e.Vertexes[1].Point.y) > 1e-6]
    return solid.makeFillet(radius, edges)


def rounded_loop_y(width, height, y0, y1, radius, band):
    """A ring along y following a rounded rectangle: the centre line is width x height."""
    outer = rounded_prism_y(width + band, height + band, y0, y1, radius + band / 2)
    inner = rounded_prism_y(width - band, height - band, y0, y1, max(radius - band / 2, 0.1))
    return outer.cut(inner)


def _rounded_wire_y(width, height, radius, y, cz):
    solid = rounded_prism_y(width, height, y, y + 1, radius, 0, cz)
    face = next(f for f in solid.Faces if abs(f.CenterOfMass.y - y) < 1e-6)
    return face.OuterWire


def tapered_prism_y(size0, radius0, y0, size1, radius1, y1, cz=0.0):
    """A solid along y blending one rounded rectangle (width, height) into another."""
    wires = [
        _rounded_wire_y(size0[0], size0[1], radius0, y0, cz),
        _rounded_wire_y(size1[0], size1[1], radius1, y1, cz),
    ]
    return Part.makeLoft(wires, True, True)


def extrude_x(points_yz, x0, x1):
    """A prism along x from a polygon given in (y, z)."""
    pts = [V(x0, y, z) for y, z in points_yz]
    wire = Part.makePolygon([*pts, pts[0]])
    return Part.Face(wire).extrude(V(x1 - x0, 0, 0))


def hexagon_z(across_flats, z0, z1, x=0.0, y=0.0):
    r = across_flats / 2 / math.cos(math.pi / 6)
    pts = [
        V(x + r * math.cos(math.radians(60 * i)), y + r * math.sin(math.radians(60 * i)), z0)
        for i in range(6)
    ]
    wire = Part.makePolygon([*pts, pts[0]])
    return Part.Face(wire).extrude(V(0, 0, z1 - z0))


def fuse(shapes):
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def cut(base, tools):
    return base.cut(fuse(tools) if len(tools) > 1 else tools[0]).removeSplitter()


def polar(radius, angle_deg):
    return radius * math.cos(math.radians(angle_deg)), radius * math.sin(math.radians(angle_deg))


def tube_along(points, radius):
    """A swept round cable through the given points."""
    vectors = [V(*p) for p in points]
    curve = Part.BSplineCurve()
    curve.interpolate(vectors)
    path = Part.Wire(curve.toShape())
    start = curve.value(curve.FirstParameter)
    tangent = curve.tangent(curve.FirstParameter)[0]
    profile = Part.Wire(Part.makeCircle(radius, start, tangent))
    return path.makePipeShell([profile], True, True)
