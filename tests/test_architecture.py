"""Keeps the structure: a light spec layer FreeCAD can import, and licensed meshes out of git."""

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spec_only_uses_the_standard_library():
    """FreeCAD's bundled Python imports spec.py: third-party imports would break the CAD build."""
    tree = ast.parse((ROOT / "src/vawt/spec.py").read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    assert names <= set(sys.stdlib_module_names), names


def test_sizing_needs_no_cad():
    code = "import sys, vawt.system.sizing; print('FreeCAD' in sys.modules, 'Part' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False False"


def test_licensed_meshes_are_ignored_by_git():
    ignored = (ROOT / ".gitignore").read_text()
    assert "cad/vendor/ugrinsky/*.3mf" in ignored
    assert "cad/vendor/ugrinsky/*.stl" in ignored
    assert "build/" in ignored  # the rendered STLs and the FCStd carry the meshes too


def test_cli_commands_import():
    from vawt.cli import COMMANDS

    for module, _ in COMMANDS.values():
        __import__(module)


def test_no_shared_number_in_freecad_scripts_for_the_pier():
    """Spot check of rule 1: the pier's size only comes from spec."""
    for path in (ROOT / "cad/freecad").glob("*.py"):
        assert "3000" not in path.read_text(), path.name
