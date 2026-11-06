#!/usr/bin/env python3
"""Writes docs/images/render-site-labelled.png: the rear site render, with named parts.

Leader lines end where Blender says each point landed in the picture
(build/render/projection-site-rear.json). Numbers come from `vawt.spec`, so they cannot drift. Needs
`rsvg-convert` and ImageMagick's `magick`.
"""

import json
import os
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vawt import spec  # noqa: E402
from vawt.spec import GENERATOR, ROTOR, SITE  # noqa: E402

SOURCE = ROOT / "docs" / "images" / "render-site-rear.png"
OUT = ROOT / "docs" / "images" / "render-site-labelled.png"
PROJECTION = ROOT / "build" / "render" / "projection-site-rear.json"
MAGICK = os.environ.get("MAGICK", "magick")
RSVG = os.environ.get("RSVG_CONVERT", "rsvg-convert")


def labels() -> list[tuple[str, str, str, str]]:
    """(point, side of the picture, title, detail)."""
    return [
        (
            "upper_bracket",
            "left",
            "Upper bracket",
            f"the model's own, {spec.rotor_tip_clearance():.0f} mm rotor to pier",
        ),
        (
            "rotor",
            "left",
            "Printed rotor",
            f"Ø{ROTOR.diameter:.0f} x {spec.rotor_height():.0f} mm, in ASA",
        ),
        (
            "generator",
            "left",
            f"Generator {GENERATOR.name}",
            f"under a rain cover; rotor underside at {spec.rotor_bottom_z() / 1000:.2f} m",
        ),
        ("conduit", "right", "Generator cable", "in M16 conduit, clipped to the pier"),
        (
            "enclosure",
            "right",
            "Enclosure",
            f"{spec.enclosure_flange_width():.0f} x {spec.enclosure_total_height():.0f} mm: "
            f"charger, {spec.battery_wh():.0f} Wh 3S pack; faces north",
        ),
        (
            "pier",
            "right",
            "Timber pier",
            f"{SITE.pier_width:.0f} x {SITE.pier_width:.0f} mm, "
            f"{SITE.pier_height / 1000:.0f} m above ground",
        ),
        ("socket", "right", "Steel ground socket", f"for the {SITE.pier_width:.0f} mm post"),
    ]  # fmt: skip


def overlay(width: int, height: int, points: dict) -> str:
    unit = width / 1800
    title_size = 30 * unit
    detail_size = 22 * unit
    box_h = 74 * unit
    box_w = 620 * unit
    margin = 28 * unit
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">']
    used = {"left": -1e9, "right": -1e9}
    for key, side, title, detail in sorted(labels(), key=lambda item: points[item[0]][1]):
        px, py = points[key][0] * width, points[key][1] * height
        y = max(py - box_h / 2, used[side] + box_h + 14 * unit)
        used[side] = y
        x = margin if side == "left" else width - margin - box_w
        anchor_x = x + box_w if side == "left" else x
        anchor_y = y + box_h / 2
        parts.append(
            f'<line x1="{anchor_x:.1f}" y1="{anchor_y:.1f}" x2="{px:.1f}" y2="{py:.1f}" '
            f'stroke="white" stroke-width="{2.4 * unit:.1f}"/>'
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{6 * unit:.1f}" fill="white" stroke="#1b2a3a" '
            f'stroke-width="{1.5 * unit:.1f}"/>'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{box_w:.1f}" height="{box_h:.1f}" '
            f'rx="{8 * unit:.1f}" fill="#101820" fill-opacity="0.78"/>'
            f'<text x="{x + 18 * unit:.1f}" y="{y + 32 * unit:.1f}" fill="white" '
            f'font-family="Helvetica" font-weight="bold" font-size="{title_size:.1f}">'
            f"{escape(title)}</text>"
            f'<text x="{x + 18 * unit:.1f}" y="{y + 60 * unit:.1f}" fill="#cfd8e0" '
            f'font-family="Helvetica" font-size="{detail_size:.1f}">{escape(detail)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    if not shutil.which(MAGICK) or not shutil.which(RSVG):
        raise SystemExit(f"needs {MAGICK} and {RSVG}")
    data = json.loads(PROJECTION.read_text())
    size = data["size"]
    work = ROOT / "build" / "render"
    svg = work / "labels.svg"
    png = work / "labels.png"
    # The picture on disk may be at another size than the last projection: fractions still hold
    picked = subprocess.run(
        [MAGICK, "identify", "-format", "%w %h", str(SOURCE)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    width, height = int(picked[0]), int(picked[1])
    _ = size
    svg.write_text(overlay(width, height, data["points"]))
    subprocess.run([RSVG, str(svg), "-o", str(png)], check=True)
    subprocess.run([MAGICK, str(SOURCE), str(png), "-composite", str(OUT)], check=True)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
