"""First-pass board from the netlist: outline, holes, footprints, nets. Runs under KiCad's Python.

    KiCad's python3 tools/kicad_place.py <netlist.xml> <board.json> <out.kicad_pcb>

Rerunning replaces the board. It is a placement for the enclosure fit check and for review, not a
layout: nothing is routed (plan electronics.md, E3). Parts are packed per schematic sheet so that
each region stays together; the terminal blocks sit on the edge that faces the cable glands.
board.json comes from `tools/build-electronics.sh`, so the spec stays the only home of the numbers.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

FOOTPRINTS = Path(
    os.environ.get(
        "KICAD_FOOTPRINT_DIR", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
    )
)
PROJECT_LIB = Path(__file__).resolve().parents[1] / "electronics" / "lib" / "footprints.pretty"
ORIGIN = (150.0, 100.0)  # board centre on the sheet; also the grid origin the 3D exports use
GAP = 1.4


def mm(v):
    return pcbnew.FromMM(v)


def to_vec(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))


def load(board, comp):
    lib, name = comp["footprint"].split(":")
    path = PROJECT_LIB if lib == "vawt" else FOOTPRINTS / f"{lib}.pretty"
    fp = pcbnew.FootprintLoad(str(path), name)
    if fp is None:
        raise SystemExit(f"footprint not found: {comp['footprint']}")
    fp.SetReference(comp["ref"])
    fp.SetValue(comp["value"])
    board.Add(fp)
    return fp


def size(fp):
    box = fp.GetBoundingBox(False)
    return pcbnew.ToMM(box.GetWidth()), pcbnew.ToMM(box.GetHeight())


def centre_at(fp, x, y):
    """Moves the footprint so the centre of its bounding box lands at (x, y) on the board."""
    fp.SetPosition(to_vec(0, 0))
    box = fp.GetBoundingBox(False)
    dx = pcbnew.ToMM(box.GetCenter().x) - ORIGIN[0]
    dy = pcbnew.ToMM(box.GetCenter().y) - ORIGIN[1]
    fp.SetPosition(to_vec(x - dx, y - dy))


def pack(parts, region, unplaced):
    """Shelf packing, tallest first. Reports what does not fit rather than overlapping it."""
    x0, y0, x1, y1 = region
    x, y, shelf = x0, y0, 0.0
    for fp in sorted(parts, key=lambda f: -size(f)[1]):
        w, h = size(fp)
        if x + w > x1:
            x, y, shelf = x0, y + shelf + GAP, 0.0
        if y + h > y1:
            unplaced.append(fp.GetReference())
            continue
        centre_at(fp, x + w / 2, y + h / 2)
        x += w + GAP
        shelf = max(shelf, h)


def main():
    netlist, spec_file, out = sys.argv[1:4]
    spec = json.loads(Path(spec_file).read_text())
    width, height = spec["width"], spec["height"]
    root = ET.parse(netlist).getroot()

    board = pcbnew.BOARD()
    board.GetDesignSettings().SetBoardThickness(mm(spec["thickness"]))
    board.SetCopperLayerCount(4)
    for x0, y0, x1, y1 in (
        (-width / 2, -height / 2, width / 2, -height / 2),
        (width / 2, -height / 2, width / 2, height / 2),
        (width / 2, height / 2, -width / 2, height / 2),
        (-width / 2, height / 2, -width / 2, -height / 2),
    ):
        edge = pcbnew.PCB_SHAPE(board)
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetStart(to_vec(x0, y0))
        edge.SetEnd(to_vec(x1, y1))
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetWidth(mm(0.1))
        board.Add(edge)
    board.GetDesignSettings().SetGridOrigin(to_vec(0, 0))
    board.GetDesignSettings().SetAuxOrigin(to_vec(0, 0))

    comps, sheets = {}, {}
    for comp in root.find("components"):
        ref = comp.get("ref")
        footprint = comp.findtext("footprint")
        if not footprint:
            raise SystemExit(f"{ref} has no footprint")
        path = comp.find("sheetpath").get("names")
        comps[ref] = {
            "ref": ref,
            "value": comp.findtext("value"),
            "footprint": footprint,
            "sheet": path,
        }
    placed = {ref: load(board, c) for ref, c in comps.items()}
    for ref, c in comps.items():
        sheets.setdefault(c["sheet"], []).append(ref)

    nets = {}
    for net in root.find("nets"):
        name = net.get("name")
        info = pcbnew.NETINFO_ITEM(board, name)
        board.Add(info)
        nets[name] = info
        for node in net:
            fp = placed.get(node.get("ref"))
            if fp is None:
                continue
            for pad in fp.Pads():
                if pad.GetNumber() == node.get("pin"):
                    pad.SetNet(info)

    # Fixed: mounting holes, terminal blocks on the lower edge (cables come up from the glands)
    i = spec["hole_inset"]
    holes = [r for r in comps if r.startswith("H")]
    for ref, (x, y) in zip(
        sorted(holes),
        (
            (-width / 2 + i, -height / 2 + i),
            (width / 2 - i, -height / 2 + i),
            (-width / 2 + i, height / 2 - i),
            (width / 2 - i, height / 2 - i),
        ),
    ):
        placed[ref].SetPosition(to_vec(x, y))

    edge_row = dict(spec["terminals"])
    fixed = set(holes)
    for ref, c in comps.items():
        if c["value"] in edge_row:
            fp = placed[ref]
            fp.SetOrientationDegrees(0)
            w, h = size(fp)
            centre_at(fp, edge_row[c["value"]], height / 2 - h / 2 - 0.6)
            fixed.add(ref)
    usb = next(r for r, c in comps.items() if c["value"] == "USB-C")
    placed[usb].SetOrientationDegrees(90)
    w, h = size(placed[usb])
    centre_at(placed[usb], width / 2 - w / 2 + 0.5, 22.0)
    fixed.add(usb)
    module = next(r for r, c in comps.items() if c["value"].startswith("ESP32"))
    placed[module].SetOrientationDegrees(0)
    w, h = size(placed[module])
    centre_at(placed[module], width / 2 - 8 - w / 2, -height / 2 + h / 2 + 0.4)
    fixed.add(module)

    top = -height / 2 + 1.0
    bottom = height / 2 - 13.0
    regions = {
        "/Input stage/": (-width / 2 + 8.5, top, -2.0, bottom),
        "/Charger/": (-1.0, top, 16.5, bottom),
        "/Controller/": (20.0, top + 26.0, width / 2 - 8.5, bottom),
    }
    unplaced = []
    for sheet, refs in sheets.items():
        pack([placed[r] for r in refs if r not in fixed], regions[sheet], unplaced)

    pcbnew.SaveBoard(out, board)
    print(f"placed {len(placed) - len(unplaced)} of {len(placed)} parts")
    if unplaced:
        raise SystemExit(f"no room for: {', '.join(unplaced)}")


if __name__ == "__main__":
    main()
