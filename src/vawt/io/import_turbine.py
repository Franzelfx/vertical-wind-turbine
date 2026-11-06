"""Extracts the rotor meshes from the 3MF to binary STL in `build/vendor/`. Standard library only.

The 3MF stays out of git (ADR-003): this step rebuilds everything from your local copy. Meshes keep
the model's own frame (see `spec.py`): all rotor sections are in the position of the assembled
rotor except for the middle section's two further copies, which CAD rotates.
"""

import hashlib
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "cad" / "vendor" / "ugrinsky" / "Ugrinsky_Wind_Turbine.3mf"
OUT = ROOT / "build" / "vendor"
SHA256 = "1c515eceada9969ea212c954686f87c28c61259d54cca958c1f73984190f6c9a"
NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
PARTS = {
    "rotor_bottom": "3D/Objects/object_1.model",
    "rotor_top": "3D/Objects/object_2.model",
    "rotor_middle": "3D/Objects/object_3.model",
    "bracket": "3D/Objects/object_4.model",
}


def read_mesh(archive: zipfile.ZipFile, name: str):
    tree = ET.fromstring(archive.read(name))
    mesh = tree.find(f"{NS}resources/{NS}object/{NS}mesh")
    vertices = [
        (float(v.get("x")), float(v.get("y")), float(v.get("z")))
        for v in mesh.find(f"{NS}vertices")
    ]
    triangles = [
        (int(t.get("v1")), int(t.get("v2")), int(t.get("v3"))) for t in mesh.find(f"{NS}triangles")
    ]
    return vertices, triangles


def write_stl(path: Path, vertices, triangles) -> None:
    with path.open("wb") as out:
        out.write(b"vawt: extracted from a licensed 3MF; do not redistribute".ljust(80))
        out.write(struct.pack("<I", len(triangles)))
        record = struct.Struct("<12fH")
        for a, b, c in triangles:
            ax, ay, az = vertices[a]
            bx, by, bz = vertices[b]
            cx, cy, cz = vertices[c]
            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            length = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
            out.write(
                record.pack(
                    nx / length, ny / length, nz / length, ax, ay, az, bx, by, bz, cx, cy, cz, 0
                )
            )


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"{SOURCE} is missing: download it from MakerWorld (cad/vendor/ugrinsky)")
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"{SOURCE.name} changed: sha256 {digest}; check it, then update SHA256")
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as archive:
        for name, member in PARTS.items():
            vertices, triangles = read_mesh(archive, member)
            write_stl(OUT / f"{name}.stl", vertices, triangles)
            print(f"wrote build/vendor/{name}.stl: {len(triangles)} triangles")


if __name__ == "__main__":
    main()
