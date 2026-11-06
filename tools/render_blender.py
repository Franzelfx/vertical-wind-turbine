"""Renders the assembly with Cycles to docs/images/render-*.png. Runs inside Blender.

blender -b --factory-startup -P tools/render_blender.py -- [--only NAME] [--samples N] [--width W]

Reads what `tools/build-cad.sh` wrote to build/render/. The charge board comes from KiCad's GLB, so
it keeps KiCad's colours.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "build" / "render"
GLB = ROOT / "build" / "kicad" / "charge-board.glb"
OUT = ROOT / "docs" / "images"

# Colour, metallic, roughness
MATERIALS = {
    "rotor": ((0.20, 0.27, 0.36), 0.0, 0.42),
    "rotor_alt": ((0.03, 0.11, 0.30), 0.35, 0.38),
    "enclosure": ((0.62, 0.63, 0.60), 0.0, 0.5),
    "enclosure_dark": ((0.34, 0.36, 0.35), 0.0, 0.5),
    "printed_dark": ((0.035, 0.038, 0.045), 0.0, 0.5),
    "rubber": ((0.015, 0.015, 0.015), 0.0, 0.7),
    "tpu": ((0.85, 0.36, 0.05), 0.0, 0.45),
    "steel": ((0.72, 0.73, 0.75), 1.0, 0.28),
    "steel_galv": ((0.62, 0.64, 0.66), 1.0, 0.48),
    "aluminium": ((0.78, 0.79, 0.80), 1.0, 0.35),
    "battery": ((0.015, 0.09, 0.32), 0.0, 0.3),
    "motor": ((0.04, 0.04, 0.05), 0.85, 0.32),
    "black": ((0.02, 0.02, 0.022), 0.0, 0.55),
    "pcb": ((0.02, 0.16, 0.06), 0.0, 0.3),
    "wire_red": ((0.6, 0.03, 0.02), 0.0, 0.4),
    "wire_black": ((0.015, 0.015, 0.015), 0.0, 0.4),
    "wire_yellow": ((0.8, 0.6, 0.03), 0.0, 0.4),
    "wire_blue": ((0.05, 0.2, 0.6), 0.0, 0.4),
    "wire_white": ((0.8, 0.8, 0.8), 0.0, 0.4),
}
SMOOTH_ANGLE = math.radians(32)
OUTDOOR = {"ground": True}

ROTOR_PARTS = ("rotor_", "bracket_top", "stub")
DRIVE_HIDE_FOR_OPEN = ("generator_cover",)
ENCLOSURE_PARTS = (
    "tub",
    "lid",
    "gasket",
    "rain_hood",
    "battery",
    "tray",
    "strap",
    "brake_resistor",
    "gland",
    "rim_screw",
    "pier_screw",
    "board",
)


def starts(name, prefixes):
    return any(name == p or name.startswith(p) for p in prefixes)


def exploded_enclosure(name):
    """Moves along y, away from the pier, in metres."""
    if name == "rain_hood" or name.startswith("pier_screw_1") or name.startswith("pier_screw_3"):
        return (0, 0, 0.11)
    if name == "lid":
        return (0, 0.20, 0)
    if name.startswith("rim_screw"):
        return (0, 0.27, 0)
    if name == "gasket":
        return (0, 0.13, 0)
    if name == "board":
        return (0, 0.09, 0)
    if name in ("battery", "strap"):
        return (0, 0.065, 0)
    if name.startswith("wire"):
        return (0, 0.0, -2.0)  # parked out of view: the explosion shows parts, not the harness
    return (0, 0, 0)


def scenes(layout):
    axis = Vector(layout["rotor_axis"]) / 1000
    height = layout["rotor_height"] / 1000
    box_origin = Vector(layout["enclosure_origin"]) / 1000
    box = Vector(layout["enclosure_size"]) / 1000
    box_mid = box_origin + Vector((0, box.y / 2, box.z / 2))
    drive_mid = axis + Vector((0, 0.05, -0.05))
    return {
        "site": {
            "direction": (-0.6, -1.0, 0.12),
            "target": (0, -0.08, 1.5),
            "distance": 6.9,
            "hide": (),
            "ground": True,
            "tall": 1.5,
        },
        "site-rear": {
            "direction": (0.85, 1.0, 0.12),
            "target": (0, -0.02, 1.5),
            "distance": 6.9,
            "hide": (),
            "ground": True,
            "tall": 1.5,
        },
        "turbine": {
            "direction": (-0.85, -1.0, -0.05),
            "target": tuple(axis + Vector((0, 0.04, height / 2))),
            "distance": 3.0,
            "hide": (),
            "ground": False,
            "tall": 1.5,
        },
        "drive": {
            "direction": (-1.0, -0.75, 0.05),
            "target": tuple(drive_mid),
            "distance": 0.95,
            "hide": (),
            "ground": False,
        },
        "drive-open": {
            "direction": (-1.0, -0.75, -0.08),
            "target": tuple(drive_mid),
            "distance": 0.95,
            "hide": ("generator_cover", "rotor_bottom"),
            "ground": False,
        },
        "enclosure": {
            "direction": (0.7, 1.0, 0.28),
            "target": tuple(box_mid),
            "distance": 0.95,
            "hide": (),
            "ground": False,
        },
        "enclosure-below": {
            "direction": (0.55, 0.9, -0.85),
            "target": tuple(box_mid + Vector((0, 0, -0.06))),
            "distance": 0.8,
            "hide": ("cable",),
            "ground": False,
        },
        "enclosure-open": {
            "direction": (0.35, 1.0, 0.25),
            "target": tuple(box_mid),
            "distance": 0.8,
            "hide": ("lid", "rain_hood", "rim_screw", "gasket"),
            "ground": False,
        },
        "enclosure-exploded": {
            "direction": (1.0, 0.75, 0.42),
            "target": tuple(box_mid + Vector((0, 0.09, 0.03))),
            "distance": 1.05,
            "hide": ("cable",),
            "ground": False,
            "offset": exploded_enclosure,
        },
    }


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_wood(made, node):
    tree = made.node_tree
    coords = tree.nodes.new("ShaderNodeTexCoord")
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (70.0, 70.0, 2.5)
    tree.links.new(coords.outputs["Object"], mapping.inputs["Vector"])
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Distortion"].default_value = 2.5
    tree.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.17, 0.08, 0.03, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.40, 0.21, 0.08, 1)
    tree.links.new(noise.outputs[0], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs[0], node.inputs["Base Color"])
    node.inputs["Roughness"].default_value = 0.72


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
    colour, metallic, roughness = MATERIALS[name]
    node.inputs["Base Color"].default_value = (*colour, 1.0)
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    return made


def import_stl(path, look):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(path), global_scale=0.001)
    for obj in set(bpy.data.objects) - before:
        obj.data.materials.append(material(look))
        mesh = obj.data
        for polygon in mesh.polygons:
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


def add_ground():
    mesh = bpy.data.meshes.new("ground")
    size = 60
    mesh.from_pydata(
        [(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)], [], [(0, 1, 2, 3)]
    )
    obj = bpy.data.objects.new("ground", mesh)
    bpy.context.collection.objects.link(obj)
    look = bpy.data.materials.new("ground")
    look.use_nodes = True
    tree = look.node_tree
    node = tree.nodes["Principled BSDF"]
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Detail"].default_value = 8.0
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    coords = tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(coords.outputs["Object"], noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 25.0
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.05, 0.13, 0.03, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.16, 0.28, 0.06, 1)
    tree.links.new(noise.outputs[0], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs[0], node.inputs["Base Color"])
    node.inputs["Roughness"].default_value = 0.95
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    tree.links.new(noise.outputs[0], bump.inputs["Height"])
    tree.links.new(bump.outputs[0], node.inputs["Normal"])
    obj.data.materials.append(look)


def sky():
    """A soft vertical gradient: stays independent of Blender's changing sky models."""
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    tree = world.node_tree
    coords = tree.nodes.new("ShaderNodeTexCoord")
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(coords.outputs["Generated"], sep.inputs[0])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.80, 0.87, 0.95, 1)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = (0.20, 0.42, 0.78, 1)
    tree.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    background = tree.nodes["Background"]
    tree.links.new(ramp.outputs[0], background.inputs[0])
    background.inputs[1].default_value = 0.85
    bpy.context.scene.world = world


def sun(direction):
    light = bpy.data.lights.new("sun", "SUN")
    light.energy = 2.4
    light.angle = math.radians(3.0)
    obj = bpy.data.objects.new("sun", light)
    bpy.context.collection.objects.link(obj)
    view = Vector(direction).normalized()
    right = view.cross(Vector((0, 0, 1))).normalized()
    towards = (view + right * 0.7 + Vector((0, 0, 0.9))).normalized()
    obj.rotation_euler = towards.to_track_quat("Z", "Y").to_euler()


def camera(direction, target, distance, aspect):
    data = bpy.data.cameras.new("camera")
    data.lens = 70
    data.sensor_width = 36
    data.clip_end = 400
    obj = bpy.data.objects.new("camera", data)
    bpy.context.collection.objects.link(obj)
    view = Vector(direction).normalized()
    obj.location = Vector(target) + view * distance
    obj.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = obj
    _ = aspect


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


def render(name, shot, samples, width):
    clear()
    manifest = json.loads((DATA / "manifest.json").read_text())
    offset_of = shot.get("offset", lambda _: (0, 0, 0))
    for item, info in manifest.items():
        if starts(item, shot["hide"]):
            continue
        offset = Vector(offset_of(item))
        if item == "board":
            if (DATA / "board_matrix.json").exists() and GLB.exists():
                import_board(offset)
                continue
        for obj in import_stl(DATA / info["file"], info["material"]):
            obj.location += offset
    bpy.context.view_layer.update()
    if shot["ground"]:
        add_ground()
    sky()
    sun(shot["direction"])
    camera(shot["direction"], shot["target"], shot["distance"], 1.6)
    use_gpu_if_there()
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = int(width * shot.get("tall", 0.625))
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / f"render-{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"wrote {scene.render.filepath}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--width", type=int, default=1600)
    args = parser.parse_args(argv)
    layout = json.loads((DATA / "layout.json").read_text())
    for name, shot in scenes(layout).items():
        if args.only is None or args.only == name:
            render(name, shot, args.samples, args.width)


main()
