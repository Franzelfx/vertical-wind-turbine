"""Renders the assembly with Cycles to docs/images/render-*.png. Runs inside Blender.

blender -b --factory-startup -P tools/render_blender.py -- [--only NAME] [--samples N] [--width W]

Reads what `tools/build-cad.sh` wrote to build/render/. The charge board comes from KiCad's GLB, so
it keeps KiCad's colours. The garden around the pier (grass, trees, sky) is only set dressing and is
made here, from a fixed random seed, so reruns give the same picture. It writes where the labelled
points land in each image to build/render/, for tools/label_render.py.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "build" / "render"
GLB = ROOT / "build" / "kicad" / "charge-board.glb"
OUT = ROOT / "docs" / "images"
SUN_ELEVATION = math.radians(38)
SMOOTH_ANGLE = math.radians(32)
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

# Colour, metallic, roughness, then extras. edge: rounded-edge radius in metres, for highlights.
# layers: (axis, period in metres), the print's layer lines. Real layers are finer than a pixel in
# all but the closest shots; this period is what still reads as a printed surface.
MATERIALS = {
    "rotor": ((0.20, 0.27, 0.36), 0.0, 0.42, {"layers": ("Z", 0.0009)}),
    "rotor_alt": ((0.03, 0.11, 0.30), 0.35, 0.38, {"layers": ("Z", 0.0009)}),
    "enclosure": ((0.62, 0.63, 0.60), 0.0, 0.5, {"edge": 0.0007, "layers": ("Y", 0.0009)}),
    "enclosure_dark": ((0.34, 0.36, 0.35), 0.0, 0.5, {"edge": 0.0007, "layers": ("Z", 0.0009)}),
    "printed_dark": ((0.035, 0.038, 0.045), 0.0, 0.5, {"edge": 0.0007, "layers": ("Z", 0.0009)}),
    "rubber": ((0.015, 0.015, 0.015), 0.0, 0.7, {}),
    "tpu": ((0.85, 0.36, 0.05), 0.0, 0.45, {"edge": 0.0005}),
    "steel": ((0.72, 0.73, 0.75), 1.0, 0.28, {"edge": 0.0003}),
    "steel_galv": ((0.62, 0.64, 0.66), 1.0, 0.48, {"edge": 0.0005, "spangle": True}),
    "aluminium": ((0.78, 0.79, 0.80), 1.0, 0.35, {"edge": 0.0005}),
    "battery": ((0.015, 0.09, 0.32), 0.0, 0.3, {"edge": 0.001}),
    "motor": ((0.04, 0.04, 0.05), 0.85, 0.32, {"edge": 0.0005}),
    "black": ((0.02, 0.02, 0.022), 0.0, 0.55, {"edge": 0.0004}),
    "conduit": ((0.02, 0.02, 0.022), 0.0, 0.5, {"rings": 0.004}),
    "pcb": ((0.02, 0.16, 0.06), 0.0, 0.3, {}),
    "wire_red": ((0.6, 0.03, 0.02), 0.0, 0.4, {}),
    "wire_black": ((0.015, 0.015, 0.015), 0.0, 0.4, {}),
    "wire_yellow": ((0.8, 0.6, 0.03), 0.0, 0.4, {}),
    "wire_blue": ((0.05, 0.2, 0.6), 0.0, 0.4, {}),
    "wire_white": ((0.8, 0.8, 0.8), 0.0, 0.4, {}),
}


def starts(name, prefixes):
    return any(name == p or name.startswith(p) for p in prefixes)


def exploded_enclosure(name):
    """Moves away from the pier and up, in metres."""
    if name in ("rain_hood", "pier_screw_1", "pier_screw_3"):
        return (0, 0, 0.11)
    if name in ("lid", "label"):
        return (0, 0.20, 0)
    if name.startswith("rim_screw"):
        return (0, 0.27, 0)
    if name == "gasket":
        return (0, 0.13, 0)
    if name == "board":
        return (0, 0.09, 0)
    if name in ("battery", "strap"):
        return (0, 0.065, 0)
    return (0, 0, 0)


def scenes(layout):
    axis = Vector(layout["rotor_axis"]) / 1000
    height = layout["rotor_height"] / 1000
    box_origin = Vector(layout["enclosure_origin"]) / 1000
    box = Vector(layout["enclosure_size"]) / 1000
    box_mid = box_origin + Vector((0, box.y / 2, box.z / 2))
    drive_mid = axis + Vector((0, 0.05, -0.05))
    wide = {"tall": 1.5, "lens": 62, "fstop": 3.5}
    close = {"lens": 70, "fstop": 5.6}
    return {
        "site": {
            **wide,
            "direction": (-0.62, -1.0, 0.02),
            "target": (0, -0.1, 1.56),
            "distance": 6.7,
            "sun": -55,
            "hide": (),
        },
        "site-rear": {
            **wide,
            # From the side the post hides nothing: rotor on one side, enclosure on the other
            "direction": (1.0, 0.55, 0.02),
            "target": (0, -0.05, 1.56),
            "distance": 6.7,
            "sun": 50,
            "hide": (),
        },
        "turbine": {
            "tall": 1.4,
            "lens": 50,
            "fstop": 8.0,
            "direction": (-0.8, -1.0, -0.42),
            "target": tuple(axis + Vector((0, 0.05, height / 2))),
            "distance": 2.75,
            "sun": -60,
            "hide": (),
        },
        "turbine-top": {
            **close,
            "direction": (-1.0, -0.85, -0.22),
            "target": tuple(axis + Vector((0, 0.06, height + 0.02))),
            "distance": 1.0,
            "sun": -55,
            "hide": (),
        },
        "drive": {
            **close,
            "direction": (-1.0, -0.75, 0.05),
            "target": tuple(drive_mid),
            "distance": 0.95,
            "sun": -50,
            "hide": (),
        },
        "drive-open": {
            **close,
            "direction": (-1.0, -0.75, -0.08),
            "target": tuple(drive_mid),
            "distance": 0.8,
            "sun": -50,
            "hide": ("generator_cover", "rotor_", "cable"),
        },
        "enclosure": {
            **close,
            "direction": (0.7, 1.0, 0.22),
            "target": tuple(box_mid),
            "distance": 1.0,
            "sun": 50,
            "hide": (),
        },
        "enclosure-below": {
            **close,
            "direction": (0.55, 0.9, -0.7),
            "target": tuple(box_mid + Vector((0, 0, -0.06))),
            "distance": 0.85,
            "sun": 45,
            "hide": ("cable",),
        },
        "enclosure-open": {
            **close,
            "direction": (0.3, 1.0, 0.2),
            "target": tuple(box_mid),
            "distance": 0.8,
            "sun": 35,
            "fill": 3.0,
            "fstop": 8.0,
            "hide": ("lid", "label", "rain_hood", "rim_screw", "gasket"),
        },
        "enclosure-exploded": {
            **close,
            "fstop": 16.0,
            "direction": (1.0, 0.75, 0.42),
            "target": tuple(box_mid + Vector((0.02, 0.1, 0.03))),
            "distance": 1.32,
            "sun": 45,
            "fill": 2.0,
            "hide": ("cable", "wire"),
            "offset": exploded_enclosure,
        },
    }


# --- materials -------------------------------------------------------------------------------


def _bump_chain(tree, node, height_socket, strength, distance=0.001):
    """Adds a bump to the shader's normal, keeping whatever already feeds it."""
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    tree.links.new(height_socket, bump.inputs["Height"])
    linked = node.inputs["Normal"].links
    if linked:
        tree.links.new(linked[0].from_socket, bump.inputs["Normal"])
    tree.links.new(bump.outputs[0], node.inputs["Normal"])


def add_wood(made, node):
    """Sawn softwood: long streaks of early and late wood along the post, then fine fibres."""
    tree = made.node_tree
    coords = tree.nodes.new("ShaderNodeNewGeometry")  # world metres: STL objects are not
    grain_map = tree.nodes.new("ShaderNodeMapping")
    grain_map.inputs["Scale"].default_value = (70.0, 70.0, 1.1)
    tree.links.new(coords.outputs["Position"], grain_map.inputs["Vector"])
    grain = tree.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Detail"].default_value = 6.0
    grain.inputs["Roughness"].default_value = 0.55
    grain.inputs["Distortion"].default_value = 0.8
    tree.links.new(grain_map.outputs["Vector"], grain.inputs["Vector"])
    fibres_map = tree.nodes.new("ShaderNodeMapping")
    fibres_map.inputs["Scale"].default_value = (1100.0, 1100.0, 9.0)
    tree.links.new(coords.outputs["Position"], fibres_map.inputs["Vector"])
    fibres = tree.nodes.new("ShaderNodeTexNoise")
    fibres.inputs["Detail"].default_value = 3.0
    tree.links.new(fibres_map.outputs["Vector"], fibres.inputs["Vector"])
    mix = tree.nodes.new("ShaderNodeMath")
    mix.operation = "MULTIPLY_ADD"
    mix.inputs[1].default_value = 0.8
    tree.links.new(grain.outputs[0], mix.inputs[0])
    tree.links.new(fibres.outputs[0], mix.inputs[2])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.62
    ramp.color_ramp.elements[0].color = (0.10, 0.045, 0.016, 1)
    ramp.color_ramp.elements[1].position = 0.98
    ramp.color_ramp.elements[1].color = (0.50, 0.29, 0.11, 1)
    tree.links.new(mix.outputs[0], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs[0], node.inputs["Base Color"])
    node.inputs["Roughness"].default_value = 0.68
    _bump_chain(tree, node, fibres.outputs[0], 0.3, 0.0008)


def add_edge(made, node, radius):
    tree = made.node_tree
    bevel = tree.nodes.new("ShaderNodeBevel")
    bevel.samples = 4
    bevel.inputs["Radius"].default_value = radius
    tree.links.new(bevel.outputs[0], node.inputs["Normal"])


def add_layers(made, node, axis, period):
    tree = made.node_tree
    coords = tree.nodes.new("ShaderNodeNewGeometry")  # world metres: STL objects are not
    wave = tree.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = axis
    wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 1.0 / (period * math.pi)
    wave.inputs["Distortion"].default_value = 0.0
    tree.links.new(coords.outputs["Position"], wave.inputs["Vector"])
    _bump_chain(tree, node, wave.outputs["Fac"], 0.1, 0.00025)


def add_spangle(made, node):
    """Hot-dip galvanising: crystals, seen as patches of brighter and duller metal."""
    tree = made.node_tree
    coords = tree.nodes.new("ShaderNodeNewGeometry")  # world metres: STL objects are not
    voronoi = tree.nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = 180.0
    tree.links.new(coords.outputs["Position"], voronoi.inputs["Vector"])
    ramp = tree.nodes.new("ShaderNodeMapRange")
    ramp.inputs["To Min"].default_value = 0.32
    ramp.inputs["To Max"].default_value = 0.6
    tree.links.new(voronoi.outputs["Color"], ramp.inputs["Value"])
    tree.links.new(ramp.outputs[0], node.inputs["Roughness"])


def add_rings(made, node, period):
    tree = made.node_tree
    coords = tree.nodes.new("ShaderNodeNewGeometry")  # world metres: STL objects are not
    wave = tree.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 1.0 / (period * math.pi)
    tree.links.new(coords.outputs["Position"], wave.inputs["Vector"])
    _bump_chain(tree, node, wave.outputs["Fac"], 0.9, 0.0012)


def material(name):
    found = bpy.data.materials.get(name)
    if found:
        return found
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    node = made.node_tree.nodes["Principled BSDF"]
    if name == "wood":
        add_wood(made, node)
        return made
    colour, metallic, roughness, extras = MATERIALS[name]
    node.inputs["Base Color"].default_value = (*colour, 1.0)
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    if "edge" in extras:
        add_edge(made, node, extras["edge"])
    if "layers" in extras:
        add_layers(made, node, *extras["layers"])
    if extras.get("spangle"):
        add_spangle(made, node)
    if "rings" in extras:
        add_rings(made, node, extras["rings"])
    return made


# --- the assembly ----------------------------------------------------------------------------


def import_stl(path, look):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(path), global_scale=0.001)
    for obj in set(bpy.data.objects) - before:
        obj.data.materials.append(material(look))
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_smooth_by_angle(angle=SMOOTH_ANGLE)
        obj.select_set(False)
        yield obj


def import_board(offset):
    """KiCad's GLB. Its frame after Blender's y-up import is the STEP frame, in metres."""
    rows = json.loads((DATA / "board_matrix.json").read_text())
    world = Matrix(rows)
    world.translation = world.translation / 1000
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    new = set(bpy.data.objects) - before
    move = Matrix.Translation(offset)
    for obj in new:
        if obj.parent is None:
            obj.matrix_world = move @ world @ obj.matrix_world


def add_label(layout, offset):
    """The warning sticker on the lid. Its text comes from the spec, through layout.json."""
    info = layout["label"]
    width, height = info["size"][0] / 1000, info["size"][1] / 1000
    origin = Vector(info["centre"]) / 1000 + Vector(offset)
    # Faces +y, reading from the front: text x runs towards -x
    frame = Matrix(((-1, 0, 0, origin.x), (0, 0, 1, origin.y), (0, 1, 0, origin.z), (0, 0, 0, 1)))

    def plate(name, w, h, z, y, rgb):
        mesh = bpy.data.meshes.new(name)
        verts = [
            (-w / 2, y - h / 2, z),
            (w / 2, y - h / 2, z),
            (w / 2, y + h / 2, z),
            (-w / 2, y + h / 2, z),
        ]
        mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.matrix_world = frame
        look = bpy.data.materials.new(name)
        look.use_nodes = True
        node = look.node_tree.nodes["Principled BSDF"]
        node.inputs["Base Color"].default_value = (*rgb, 1)
        node.inputs["Roughness"].default_value = 0.35
        mesh.materials.append(look)

    plate("label_back", width, height, 0.0002, 0.0, (0.80, 0.55, 0.01))
    plate("label_face", width - 0.003, height - 0.003, 0.0003, 0.0, (0.86, 0.86, 0.82))
    plate("label_bar", width - 0.003, height * 0.32, 0.0004, height * 0.32, (0.80, 0.55, 0.01))

    font = bpy.data.fonts.load(FONT) if Path(FONT).exists() else None
    ink = bpy.data.materials.new("label_ink")
    ink.use_nodes = True
    ink.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        0.01,
        0.01,
        0.01,
        1,
    )
    rows = [
        (info["lines"][0], 0.0066, height * 0.32),
        (info["lines"][1], 0.0054, height * 0.03),
        (info["lines"][2], 0.0043, -height * 0.17),
        (info["lines"][3], 0.0043, -height * 0.34),
    ]
    for i, (text, size, y) in enumerate(rows):
        curve = bpy.data.curves.new(f"label_{i}", "FONT")
        curve.body = text
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.size = size
        if font:
            curve.font = font
        curve.materials.append(ink)
        obj = bpy.data.objects.new(f"label_{i}", curve)
        bpy.context.collection.objects.link(obj)
        obj.matrix_world = frame @ Matrix.Translation((0, y, 0.0005))


# --- the garden ------------------------------------------------------------------------------


def add_ground():
    mesh = bpy.data.meshes.new("ground")
    size = 500
    mesh.from_pydata(
        [(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)], [], [(0, 1, 2, 3)]
    )
    obj = bpy.data.objects.new("ground", mesh)
    bpy.context.collection.objects.link(obj)
    look = bpy.data.materials.new("ground")
    look.use_nodes = True
    tree = look.node_tree
    node = tree.nodes["Principled BSDF"]
    coords = tree.nodes.new("ShaderNodeTexCoord")
    fine = tree.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 180.0
    fine.inputs["Detail"].default_value = 8.0
    broad = tree.nodes.new("ShaderNodeTexNoise")
    broad.inputs["Scale"].default_value = 0.22
    broad.inputs["Detail"].default_value = 5.0
    for noise in (fine, broad):
        tree.links.new(coords.outputs["Object"], noise.inputs["Vector"])
    add = tree.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 0.5
    tree.links.new(fine.outputs[0], add.inputs[0])
    tree.links.new(broad.outputs[0], add.inputs[2])
    half = tree.nodes.new("ShaderNodeMath")
    half.operation = "MULTIPLY"
    half.inputs[1].default_value = 0.72
    tree.links.new(add.outputs[0], half.inputs[0])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.022, 0.06, 0.012, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.075, 0.15, 0.03, 1)
    tree.links.new(half.outputs[0], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs[0], node.inputs["Base Color"])
    node.inputs["Roughness"].default_value = 0.95
    node.inputs[
        "Specular IOR Level"
    ].default_value = 0.08  # or far ground mirrors the sky at a low angle
    _bump_chain(tree, node, fine.outputs[0], 0.7, 0.02)
    obj.data.materials.append(look)


def add_grass(count=700_000, reach=30.0, seed=7):
    """Grass blades as plain triangles around the pier: dense close by, larger far away."""
    rng = np.random.default_rng(seed)
    r = reach * rng.random(count) ** 1.9
    a = rng.random(count) * 2 * np.pi
    x, y = r * np.cos(a), r * np.sin(a)
    grow = 1.0 + (r / 4.0) ** 1.7
    length = rng.uniform(0.05, 0.13, count) * (1 + 0.35 * grow)
    width = rng.uniform(0.0028, 0.0058, count) * grow
    lean = rng.random(count) * 2 * np.pi
    bend = rng.uniform(0.15, 0.75, count) * length
    side = rng.random(count) * 2 * np.pi
    ts = np.array([0.0, 0.0, 0.42, 0.42, 0.78, 0.78, 1.0])
    edge = np.array([-1.0, 1.0, -0.85, 0.85, -0.5, 0.5, 0.0])
    t = ts[None, :]
    verts = np.empty((count, 7, 3), np.float32)
    verts[:, :, 0] = (
        x[:, None]
        + np.cos(lean)[:, None] * bend[:, None] * t**2
        + np.cos(side)[:, None] * width[:, None] / 2 * edge[None, :]
    )
    verts[:, :, 1] = (
        y[:, None]
        + np.sin(lean)[:, None] * bend[:, None] * t**2
        + np.sin(side)[:, None] * width[:, None] / 2 * edge[None, :]
    )
    verts[:, :, 2] = length[:, None] * t * (1 - 0.25 * t * (bend / length)[:, None])
    tris = np.array([[0, 1, 2], [1, 3, 2], [2, 3, 4], [3, 5, 4], [4, 5, 6]], np.int32)
    faces = tris[None, :, :] + (np.arange(count, dtype=np.int32) * 7)[:, None, None]

    mesh = bpy.data.meshes.new("grass")
    mesh.vertices.add(count * 7)
    mesh.vertices.foreach_set("co", verts.reshape(-1))
    mesh.loops.add(count * 15)
    mesh.loops.foreach_set("vertex_index", faces.reshape(-1))
    mesh.polygons.add(count * 5)
    mesh.polygons.foreach_set("loop_start", np.arange(count * 5, dtype=np.int32) * 3)
    mesh.update(calc_edges=True)

    tint = rng.random(count)
    light = np.array((0.16, 0.30, 0.05))
    dark = np.array((0.035, 0.11, 0.018))
    dry = np.array((0.34, 0.33, 0.11))
    colours = dark + (light - dark) * tint[:, None]
    colours[rng.random(count) < 0.05] = dry
    shade = np.linspace(0.45, 1.15, 7)[None, :, None]
    per_vertex = (colours[:, None, :] * shade).reshape(-1, 3)
    rgba = np.concatenate([per_vertex, np.ones((count * 7, 1))], axis=1).astype(np.float32)
    attribute = mesh.color_attributes.new("tint", "FLOAT_COLOR", "POINT")
    attribute.data.foreach_set("color", rgba.reshape(-1))

    obj = bpy.data.objects.new("grass", mesh)
    bpy.context.collection.objects.link(obj)
    look = bpy.data.materials.new("grass")
    look.use_nodes = True
    tree = look.node_tree
    node = tree.nodes["Principled BSDF"]
    tint_node = tree.nodes.new("ShaderNodeVertexColor")
    tint_node.layer_name = "tint"
    tree.links.new(tint_node.outputs["Color"], node.inputs["Base Color"])
    node.inputs["Roughness"].default_value = 0.55
    translucent = tree.nodes.new("ShaderNodeBsdfTranslucent")
    tree.links.new(tint_node.outputs["Color"], translucent.inputs["Color"])
    mix = tree.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.35
    tree.links.new(node.outputs[0], mix.inputs[1])
    tree.links.new(translucent.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], tree.nodes["Material Output"].inputs["Surface"])
    mesh.materials.append(look)


def add_trees(radius, low, high, colour, seed, segments=4320, crowns=1500):
    """A far ring of trees: the outline is the top of many round crowns, like a real hedge line."""
    rng = np.random.default_rng(seed)
    angle = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    top = np.full(segments, low * 0.6)
    for _ in range(crowns):
        centre = rng.random() * 2 * np.pi
        tall = rng.uniform(low, high)
        half_width = rng.uniform(0.2, 0.5) * tall / radius
        gap = np.abs((angle - centre + np.pi) % (2 * np.pi) - np.pi) / half_width
        inside = gap < 1
        crown = np.zeros(segments)
        crown[inside] = tall * (0.6 + 0.4 * np.sqrt(1 - gap[inside] ** 2))
        top = np.maximum(top, crown)
    bottom = [(radius * math.cos(a), radius * math.sin(a), 0.0) for a in angle]
    upper = [
        (radius * math.cos(a), radius * math.sin(a), float(z))
        for a, z in zip(angle, top, strict=True)
    ]
    faces = [
        (i, (i + 1) % segments, segments + (i + 1) % segments, segments + i)
        for i in range(segments)
    ]
    mesh = bpy.data.meshes.new(f"trees{seed}")
    mesh.from_pydata(bottom + upper, [], faces)
    obj = bpy.data.objects.new(f"trees{seed}", mesh)
    bpy.context.collection.objects.link(obj)
    look = bpy.data.materials.new(f"trees{seed}")
    look.use_nodes = True
    tree = look.node_tree
    node = tree.nodes["Principled BSDF"]
    coords = tree.nodes.new("ShaderNodeTexCoord")
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 12.0
    noise.inputs["Roughness"].default_value = 0.62
    tree.links.new(coords.outputs["Object"], noise.inputs["Vector"])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.36
    ramp.color_ramp.elements[0].color = (colour[0] * 0.3, colour[1] * 0.3, colour[2] * 0.3, 1)
    ramp.color_ramp.elements[1].position = 0.66
    ramp.color_ramp.elements[1].color = (*colour, 1)
    tree.links.new(noise.outputs[0], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs[0], node.inputs["Base Color"])
    node.inputs["Roughness"].default_value = 0.9
    mesh.materials.append(look)


def sky(sun_rotation):
    """A physically based sky with soft clouds, projected from the view direction onto a layer."""
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    tree = world.node_tree
    background = tree.nodes["Background"]
    texture = tree.nodes.new("ShaderNodeTexSky")
    texture.sky_type = "MULTIPLE_SCATTERING"
    texture.sun_disc = False  # the lamp below is the sun, so its strength can be set separately
    texture.sun_elevation = SUN_ELEVATION
    texture.sun_rotation = sun_rotation
    texture.altitude = 300.0
    texture.aerosol_density = 0.9
    coords = tree.nodes.new("ShaderNodeTexCoord")
    split = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(coords.outputs["Generated"], split.inputs[0])
    depth = tree.nodes.new("ShaderNodeMath")
    depth.operation = "ADD"
    depth.inputs[1].default_value = 0.12
    tree.links.new(split.outputs["Z"], depth.inputs[0])
    px = tree.nodes.new("ShaderNodeMath")
    px.operation = "DIVIDE"
    tree.links.new(split.outputs["X"], px.inputs[0])
    tree.links.new(depth.outputs[0], px.inputs[1])
    py = tree.nodes.new("ShaderNodeMath")
    py.operation = "DIVIDE"
    tree.links.new(split.outputs["Y"], py.inputs[0])
    tree.links.new(depth.outputs[0], py.inputs[1])
    join = tree.nodes.new("ShaderNodeCombineXYZ")
    tree.links.new(px.outputs[0], join.inputs["X"])
    tree.links.new(py.outputs[0], join.inputs["Y"])
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.15
    noise.inputs["Detail"].default_value = 12.0
    noise.inputs["Roughness"].default_value = 0.56
    tree.links.new(join.outputs[0], noise.inputs["Vector"])
    shape = tree.nodes.new("ShaderNodeMapRange")
    shape.inputs["From Min"].default_value = 0.46
    shape.inputs["From Max"].default_value = 0.7
    tree.links.new(noise.outputs[0], shape.inputs["Value"])
    fade = tree.nodes.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = 0.015
    fade.inputs["From Max"].default_value = 0.2
    tree.links.new(split.outputs["Z"], fade.inputs["Value"])
    amount = tree.nodes.new("ShaderNodeMath")
    amount.operation = "MULTIPLY"
    tree.links.new(shape.outputs[0], amount.inputs[0])
    tree.links.new(fade.outputs[0], amount.inputs[1])
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    tree.links.new(amount.outputs[0], mix.inputs["Factor"])
    tree.links.new(texture.outputs[0], mix.inputs["A"])
    mix.inputs["B"].default_value = (4.6, 4.6, 4.7, 1.0)
    tree.links.new(mix.outputs["Result"], background.inputs[0])
    background.inputs[1].default_value = 0.3
    bpy.context.scene.world = world


def sun(direction, side_deg):
    """Keeps the same height in every shot, off to the side of the camera so shape reads."""
    light = bpy.data.lights.new("sun", "SUN")
    light.energy = 3.0
    light.angle = math.radians(1.6)
    light.color = (1.0, 0.96, 0.9)
    obj = bpy.data.objects.new("sun", light)
    bpy.context.collection.objects.link(obj)
    view = Vector((direction[0], direction[1], 0)).normalized()
    azimuth = math.atan2(view.y, view.x) + math.radians(side_deg)
    towards = Vector(
        (
            math.cos(azimuth) * math.cos(SUN_ELEVATION),
            math.sin(azimuth) * math.cos(SUN_ELEVATION),
            math.sin(SUN_ELEVATION),
        )
    )
    obj.rotation_euler = towards.to_track_quat("Z", "Y").to_euler()
    return azimuth


def fill_light(location, target, power):
    light = bpy.data.lights.new("fill", "AREA")
    light.size = 0.7
    light.energy = power
    obj = bpy.data.objects.new("fill", light)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()


def camera(shot):
    data = bpy.data.cameras.new("camera")
    data.lens = shot.get("lens", 70)
    data.sensor_width = 36
    data.clip_end = 2000
    data.dof.use_dof = True
    data.dof.focus_distance = shot["distance"]
    data.dof.aperture_fstop = shot.get("fstop", 8.0)
    obj = bpy.data.objects.new("camera", data)
    bpy.context.collection.objects.link(obj)
    view = Vector(shot["direction"]).normalized()
    obj.location = Vector(shot["target"]) + view * shot["distance"]
    obj.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = obj
    return obj


def use_gpu_if_there():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = "GPU"
    except (KeyError, TypeError, AttributeError):
        scene.cycles.device = "CPU"


def render(name, shot, samples, width, layout):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    manifest = json.loads((DATA / "manifest.json").read_text())
    offset_of = shot.get("offset", lambda _: (0, 0, 0))
    for item, info in manifest.items():
        if starts(item, shot["hide"]):
            continue
        offset = Vector(offset_of(item))
        if item == "board" and (DATA / "board_matrix.json").exists() and GLB.exists():
            import_board(offset)
            continue
        look = "conduit" if item == "cable" else info["material"]
        for obj in import_stl(DATA / info["file"], look):
            obj.location += offset
    if not starts("label", shot["hide"]):
        add_label(layout, offset_of("label"))
    bpy.context.view_layer.update()
    add_ground()
    add_grass()
    add_trees(110.0, 3.5, 8.5, (0.11, 0.2, 0.055), 3)
    add_trees(300.0, 9.0, 17.0, (0.2, 0.28, 0.26), 5)
    azimuth = sun(shot["direction"], shot.get("sun", 50))
    sky(math.pi / 2 - azimuth)
    cam = camera(shot)
    if "fill" in shot:
        view = Vector(shot["direction"]).normalized()
        fill_light(Vector(shot["target"]) + view * 0.9, shot["target"], shot["fill"] * 8)
    use_gpu_if_there()
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = int(width * shot.get("tall", 0.625))
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    scene.cycles.max_bounces = 8
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    scene.view_settings.exposure = 0.25
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / f"render-{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"wrote {scene.render.filepath}")
    # Where the labelled points landed, as fractions of the image from the top left
    points = {}
    for key, position in layout.get("callouts", {}).items():
        at = world_to_camera_view(scene, cam, Vector(position) / 1000)
        points[key] = [at.x, 1.0 - at.y]
    size = [scene.render.resolution_x, scene.render.resolution_y]
    (DATA / f"projection-{name}.json").write_text(json.dumps({"size": size, "points": points}))


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--width", type=int, default=1800)
    args = parser.parse_args(argv)
    layout = json.loads((DATA / "layout.json").read_text())
    for name, shot in scenes(layout).items():
        if args.only is None or args.only == name:
            render(name, shot, args.samples, args.width, layout)


main()
