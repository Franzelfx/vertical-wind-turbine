"""Colours the assembly. Run once inside FreeCAD's GUI: Macro > Macros, or paste into its console.

freecadcmd cannot store view properties, so build/cad/wind-turbine.FCStd opens in default grey. Open
it, run this, save. Rebuilding replaces the file, so run it again after tools/build-cad.sh.
"""

import json
from pathlib import Path

import FreeCAD as App

LOOKS = {
    "rotor": (0.42, 0.50, 0.60),
    "rotor_alt": (0.13, 0.30, 0.55),
    "enclosure": (0.80, 0.81, 0.78),
    "enclosure_dark": (0.55, 0.57, 0.56),
    "printed_dark": (0.15, 0.16, 0.18),
    "rubber": (0.05, 0.05, 0.05),
    "tpu": (0.85, 0.36, 0.05),
    "steel": (0.72, 0.73, 0.75),
    "steel_galv": (0.62, 0.64, 0.66),
    "aluminium": (0.78, 0.79, 0.80),
    "battery": (0.05, 0.22, 0.55),
    "motor": (0.08, 0.08, 0.09),
    "black": (0.05, 0.05, 0.05),
    "pcb": (0.05, 0.35, 0.15),
    "wood": (0.62, 0.38, 0.17),
    "wire_red": (0.7, 0.05, 0.05),
    "wire_black": (0.05, 0.05, 0.05),
    "wire_yellow": (0.85, 0.65, 0.05),
    "wire_blue": (0.1, 0.25, 0.7),
    "wire_white": (0.85, 0.85, 0.85),
}

doc = App.ActiveDocument
colours = json.loads(Path(doc.FileName).with_name("colours.json").read_text())
for name, look in colours.items():
    obj = doc.getObject(name)
    if obj is not None and hasattr(obj.ViewObject, "ShapeColor"):
        obj.ViewObject.ShapeColor = LOOKS[look]
