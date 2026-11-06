"""Generate KiCad schematics from Python net lists (ADR-012).

A sheet is a list of parts; every pin is either connected to a named net or explicitly marked
not connected. The generator copies the symbols from the KiCad and project libraries, places
the parts in a grid, puts a net label on every pin (no wires) and writes one .kicad_sch per
sheet plus a root sheet. Nets used on more than one sheet get global labels. PWR_FLAGs are
added to nets whose power inputs have no power output. UUIDs are derived from the reference,
so regenerating gives stable files.

Usage (from a board script, see electronics/charge-board/schematic/build.py):
    s = Sheet("Power path", "power_path")
    s.part("Device:R", "R", "10k", FP_R0402, {"1": "PACK_P", "2": "GND"})
    write_project(root_file, root_uuid, project_name, [s, ...], lib_dirs)
"""

import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

KICAD_SYMBOLS = Path(os.environ.get("KICAD_SYMBOL_DIR", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"))
NS = uuid.UUID("2c0c5d8e-8d0b-4f7a-9f0c-1d1c6f6b9a33")
GRID = 1.27
FONT = "(effects (font (size 1.27 1.27)){extra})"
NC = None  # marks a pin as not connected


# --- s-expressions ---------------------------------------------------------------------------


class Q(str):
    """A quoted string atom."""


def parse(text: str):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        elif t.startswith('"'):
            cur.append(Q(t[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            cur.append(t)
    return cur[0]


def dump(node, indent=0) -> str:
    if isinstance(node, Q):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if not isinstance(node, list):
        return str(node)
    simple = all(not isinstance(x, list) for x in node)
    if simple or len(dump_flat(node)) < 100:
        return dump_flat(node)
    pad = "\t" * (indent + 1)
    inner = "\n".join(pad + dump(x, indent + 1) for x in node[1:])
    return f"({dump(node[0])}\n{inner}\n{chr(9) * indent})"


def dump_flat(node) -> str:
    if isinstance(node, list):
        return "(" + " ".join(dump_flat(x) for x in node) + ")"
    return dump(node)


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def first(node, key):
    found = find(node, key)
    return found[0] if found else None


# --- libraries -------------------------------------------------------------------------------


@dataclass
class Pin:
    number: str
    name: str
    kind: str
    x: float
    y: float
    angle: int
    unit: int
    hidden: bool


@dataclass
class LibSymbol:
    lib_id: str
    sexp: list  # flattened, named lib_id
    pins: list[Pin]
    units: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1 in symbol coordinates (y up)

    def unit_pins(self, unit: int) -> list[Pin]:
        return [p for p in self.pins if p.unit in (0, unit)]


class Libraries:
    def __init__(self, extra: dict[str, Path]):
        self.files = {**{p.stem: p for p in KICAD_SYMBOLS.glob("*.kicad_sym")}, **extra}
        self._parsed: dict[str, list] = {}
        self._cache: dict[str, LibSymbol] = {}

    def _lib(self, nick: str) -> list:
        if nick not in self._parsed:
            self._parsed[nick] = parse(self.files[nick].read_text())
        return self._parsed[nick]

    def _raw(self, nick: str, name: str) -> list:
        for s in find(self._lib(nick), "symbol"):
            if s[1] == name:
                return s
        raise KeyError(f"{nick}:{name} not found")

    def get(self, lib_id: str) -> LibSymbol:
        if lib_id in self._cache:
            return self._cache[lib_id]
        nick, name = lib_id.split(":", 1)
        raw = self._raw(nick, name)
        ext = first(raw, "extends")
        if ext:
            parent = _deepcopy(self._raw(nick, ext[1]))
            props = {p[1]: p for p in find(raw, "property")}
            body = [x for x in parent[2:] if not (isinstance(x, list) and x[0] == "property")]
            body = [_rename_units(x, ext[1], name) for x in body]
            merged = [p for p in find(parent, "property") if p[1] not in props] + list(props.values())
            raw = ["symbol", Q(name)] + merged + body
        sym = _deepcopy(raw)
        sym[1] = Q(lib_id)
        self._cache[lib_id] = LibSymbol(lib_id, sym, *_pins_and_box(sym, name))
        return self._cache[lib_id]


def _deepcopy(x):
    if isinstance(x, list):
        return [_deepcopy(y) for y in x]
    return Q(x) if isinstance(x, Q) else x


def _rename_units(node, old, new):
    if isinstance(node, list) and node and node[0] == "symbol" and isinstance(node[1], Q):
        node = list(node)
        node[1] = Q(re.sub(rf"^{re.escape(old)}_", f"{new}_", node[1]))
    return node


def _pins_and_box(sym, name):
    pins, xs, ys, units = [], [0.0], [0.0], 1
    for sub in find(sym, "symbol"):
        m = re.match(rf"^{re.escape(name)}_(\d+)_(\d+)$", sub[1])
        if not m:
            continue
        unit, style = int(m.group(1)), int(m.group(2))
        if style not in (0, 1):
            continue
        units = max(units, unit)
        for item in sub[2:]:
            if not isinstance(item, list):
                continue
            if item[0] == "pin":
                at = first(item, "at")
                pins.append(Pin(first(item, "number")[1], first(item, "name")[1], item[1],
                                float(at[1]), float(at[2]), int(float(at[3])), unit,
                                "hide" in item or first(item, "hide") is not None))
                xs.append(float(at[1]))
                ys.append(float(at[2]))
            elif item[0] in ("rectangle",):
                for key in ("start", "end"):
                    pt = first(item, key)
                    xs.append(float(pt[1]))
                    ys.append(float(pt[2]))
            elif item[0] == "polyline":
                for pt in find(first(item, "pts"), "xy"):
                    xs.append(float(pt[1]))
                    ys.append(float(pt[2]))
    return pins, units, (min(xs), min(ys), max(xs), max(ys))


# --- schematic model -------------------------------------------------------------------------


@dataclass
class Part:
    lib_id: str
    ref: str
    value: str
    footprint: str
    nets: dict  # pin number or pin name -> net name or NC
    unit: int = 1
    fields: dict = field(default_factory=dict)
    section: str = ""
    rest_nc: bool = False  # part(..., rest="nc"): unassigned non-power pins become NC (MCUs)
    in_bom: bool = True  # False for pads and test points (not assembled)


@dataclass(eq=False)
class PinRef:
    """A pin of a part (number or name) as a field value, written as "<ref>:<pin>" once the
    references are assigned. Example: the `Decouples` field of a capacitor (Phase E7 layout)."""

    part: Part
    pin: str

    def __str__(self) -> str:
        return f"{self.part.ref}:{self.pin}"


@dataclass
class Sheet:
    title: str
    name: str  # file stem
    parts: list[Part] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    _section: str = ""

    def section(self, title: str) -> None:
        self._section = title

    def part(self, lib_id, prefix, value, footprint, nets, unit=1, ref=None, rest=None,
             bom=True, **fields) -> Part:
        p = Part(lib_id, ref or prefix, value, footprint, nets, unit, fields, self._section,
                 rest_nc=rest == "nc", in_bom=bom)
        self.parts.append(p)
        return p

    def note(self, text: str) -> None:
        self.notes.append(text)


def _uuid(*parts) -> str:
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


def _snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


def _fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".")


class Project:
    def __init__(self, name: str, root_uuid: str, libs: Libraries, sheets: list[Sheet]):
        self.name, self.root_uuid, self.libs, self.sheets = name, root_uuid, libs, sheets
        self._assign_refs()
        self._resolve()

    def _assign_refs(self):
        counters: dict[str, int] = {}
        named: dict[int, str] = {}
        for sheet in self.sheets:
            for p in sheet.parts:
                if p.ref.endswith("?") or not p.ref[-1].isdigit():
                    prefix = p.ref.rstrip("?")
                    key = id(p.fields.get("same_as")) if p.fields.get("same_as") else None
                    if key and key in named:
                        p.ref = named[key]
                        continue
                    counters[prefix] = counters.get(prefix, 0) + 1
                    p.ref = f"{prefix}{counters[prefix]}"
                    named[id(p)] = p.ref

    def _resolve(self):
        """Map every pin to a net; check completeness; collect net usage per sheet."""
        self.pin_nets: dict[int, dict[str, object]] = {}
        self.net_sheets: dict[str, set[str]] = {}
        self.net_kinds: dict[str, set[str]] = {}
        errors = []
        for sheet in self.sheets:
            for p in sheet.parts:
                sym = self.libs.get(p.lib_id)
                pins = sym.unit_pins(p.unit)
                by_num = {pin.number: pin for pin in pins}
                by_name: dict[str, list[Pin]] = {}
                for pin in pins:
                    by_name.setdefault(pin.name, []).append(pin)
                mapping: dict[str, object] = {}
                for key, net in p.nets.items():
                    if key in by_num:
                        targets = [by_num[key]]
                    elif key in by_name:
                        targets = by_name[key]
                    else:
                        errors.append(f"{p.ref}: no pin '{key}' in {p.lib_id} unit {p.unit}")
                        continue
                    for pin in targets:
                        mapping[pin.number] = net
                for pin in pins:
                    if pin.number not in mapping:
                        if pin.kind == "no_connect" or (p.rest_nc and pin.kind not in ("power_in", "power_out")):
                            mapping[pin.number] = NC
                        else:
                            errors.append(f"{p.ref} ({p.value}) pin {pin.number} {pin.name}: not assigned")
                self.pin_nets[id(p)] = mapping
                for num, net in mapping.items():
                    if net is NC:
                        continue
                    self.net_sheets.setdefault(net, set()).add(sheet.name)
                    self.net_kinds.setdefault(net, set()).add(by_num[num].kind)
        if errors:
            raise ValueError("schematic errors:\n  " + "\n  ".join(errors))
        # power flags on nets with power inputs but no power output
        flags = 0
        for net, kinds in sorted(self.net_kinds.items()):
            if "power_in" in kinds and "power_out" not in kinds:
                sheet = next(s for s in self.sheets if s.name in self.net_sheets[net])
                flags += 1
                flag = Part("power:PWR_FLAG", f"#FLG{flags:02d}", "PWR_FLAG", "", {"1": net},
                            section="Power flags")
                sheet.parts.append(flag)
                self.pin_nets[id(flag)] = {"1": net}

    def is_global(self, net: str) -> bool:
        return len(self.net_sheets.get(net, ())) > 1

    # --- writing -----------------------------------------------------------------------------

    def write(self, root_path: Path) -> list[Path]:
        written = []
        for sheet in self.sheets:
            path = root_path.parent / f"{sheet.name}.kicad_sch"
            path.write_text(self._sheet_text(sheet))
            written.append(path)
        root_path.write_text(self._root_text())
        written.append(root_path)
        return written

    def _sheet_uuid(self, sheet: Sheet) -> str:
        return _uuid(self.name, "sheet", sheet.name)

    def _root_text(self) -> str:
        items = []
        for i, sheet in enumerate(self.sheets):
            x, y = 25.4 + (i % 4) * 63.5, 38.1 + (i // 4) * 38.1
            su = self._sheet_uuid(sheet)
            items.append(
                f'(sheet (at {_fmt(x)} {_fmt(y)}) (size 50.8 25.4) (fields_autoplaced yes) '
                f'(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid "{su}") '
                f'(property "Sheetname" "{sheet.title}" (at {_fmt(x)} {_fmt(y - 0.7)} 0) '
                f'{FONT.format(extra=" (justify left bottom)")}) '
                f'(property "Sheetfile" "{sheet.name}.kicad_sch" (at {_fmt(x)} {_fmt(y + 26)} 0) '
                f'{FONT.format(extra=" (justify left top)")}) '
                f'(instances (project "{self.name}" (path "/{self.root_uuid}" (page "{i + 2}")))))'
            )
        body = "\n\t".join(items)
        return (
            f'(kicad_sch (version 20250114) (generator "schgen") (generator_version "1.0") '
            f'(uuid "{self.root_uuid}") (paper "A4")\n'
            f'\t(title_block (title "{self.name}") (comment 1 "Generated by tools/schgen.py - do not edit, '
            f'edit the Python sheet definitions"))\n'
            f'\t(lib_symbols)\n\t{body}\n\t(sheet_instances (path "/" (page "1")))\n)\n'
        )

    def _sheet_text(self, sheet: Sheet) -> str:
        su = self._sheet_uuid(sheet)
        path = f"/{self.root_uuid}/{su}"
        used = sorted({p.lib_id for p in sheet.parts})
        lib_syms = "\n\t\t".join(dump(self.libs.get(lid).sexp, 2) for lid in used)
        items = self._layout(sheet, path)
        w, h = self._paper
        notes_txt = "".join(
            f'\n\t(text "{n}" (exclude_from_sim no) (at 12.7 {_fmt(h - 12.7 - 5.08 * i)} 0) '
            f'{FONT.format(extra=" (justify left bottom)")} (uuid "{_uuid(su, "note", i)}"))'
            for i, n in enumerate(sheet.notes))
        return (
            f'(kicad_sch (version 20250114) (generator "schgen") (generator_version "1.0") '
            f'(uuid "{su}") (paper "User" {_fmt(w)} {_fmt(h)})\n'
            f'\t(title_block (title "{sheet.title}") (comment 1 "Generated by tools/schgen.py - '
            f'edit the Python sheet definitions, not this file"))\n'
            f'\t(lib_symbols\n\t\t{lib_syms}\n\t)\n\t' + "\n\t".join(items) + notes_txt + "\n)\n"
        )

    def _layout(self, sheet: Sheet, path: str):
        items = []
        margin, x, y, row_h = 20.32, 20.32, 30.48, 0.0
        max_w = 0.0
        width_limit = 520.0
        last_section = None
        for p in sheet.parts:
            sym = self.libs.get(p.lib_id)
            pins = sym.unit_pins(p.unit)
            mapping = self.pin_nets[id(p)]
            x0, y0, x1, y1 = _unit_box(sym, p.unit)
            label_w = {"L": 0.0, "R": 0.0, "T": 0.0, "B": 0.0}
            for pin in pins:
                net = mapping.get(pin.number)
                text = 2.54 if net is NC else 1.0 * len(str(net)) + 6.0
                side = {0: "L", 180: "R", 90: "B", 270: "T"}[pin.angle % 360]
                label_w[side] = max(label_w[side], text)
            bw = (x1 - x0) + label_w["L"] + label_w["R"] + 10.16
            bh = (y1 - y0) + label_w["T"] + label_w["B"] + 17.78
            if p.section != last_section:
                if x > margin:
                    y += row_h + 7.62
                    x, row_h = margin, 0.0
                if p.section:
                    items.append(
                        f'(text "{p.section}" (exclude_from_sim no) (at {_fmt(x)} {_fmt(y)} 0) '
                        f'(effects (font (size 2.54 2.54) (bold yes)) (justify left bottom)) '
                        f'(uuid "{_uuid(path, "section", p.section)}"))')
                y += 7.62
                last_section = p.section
            if x + bw > width_limit and x > margin:
                y += row_h + 5.08
                x, row_h = margin, 0.0
            ox = _snap(x + label_w["L"] + 5.08 - x0)
            oy = _snap(y + label_w["T"] + 6.35 + y1)  # symbol y up -> sheet y down
            text_x = _snap(ox + x0)
            ref_xy = (text_x, _snap(oy - y1 - label_w["T"] - 2.54))
            val_xy = (text_x, _snap(oy - y0 + label_w["B"] + 3.81))
            items.append(self._symbol(p, sym, ox, oy, path, ref_xy, val_xy))
            for pin in pins:
                items.append(self._pin_item(p, pin, mapping.get(pin.number), ox, oy, path))
            x += bw
            row_h = max(row_h, bh)
            max_w = max(max_w, x)
        self._paper = (max(max_w + margin, 297.0), max(y + row_h + margin + 5.08 * len(sheet.notes), 210.0))
        return items

    def _symbol(self, p: Part, sym: LibSymbol, ox: float, oy: float, path: str,
                ref_xy: tuple[float, float], val_xy: tuple[float, float]) -> str:
        su = _uuid(path, p.ref, p.unit)
        is_power = p.lib_id.startswith("power:")
        hide = " (hide yes)"
        props = [
            ("Reference", p.ref, *ref_xy, " (justify left)" + (hide if is_power else "")),
            ("Value", p.value, *val_xy, " (justify left)"),
            ("Footprint", p.footprint, ox, oy, hide),
            ("Datasheet", p.fields.get("datasheet", "~"), ox, oy, hide),
        ]
        for k, v in p.fields.items():
            if k in ("same_as", "datasheet"):
                continue
            props.append((k, str(v), ox, oy, hide))
        if p.section and not is_power:  # functional group for the layout (Phase E7)
            props.append(("Section", p.section, ox, oy, hide))
        prop_txt = " ".join(
            f'(property "{k}" "{v}" (at {_fmt(px)} {_fmt(py)} 0) {FONT.format(extra=extra)})'
            for k, v, px, py, extra in props)
        pins = " ".join(f'(pin "{pin.number}" (uuid "{_uuid(su, "pin", pin.number)}"))'
                        for pin in sym.unit_pins(p.unit))
        return (
            f'(symbol (lib_id "{p.lib_id}") (at {_fmt(ox)} {_fmt(oy)} 0) (unit {p.unit}) '
            f'(exclude_from_sim no) (in_bom {"yes" if p.in_bom and not is_power else "no"}) '
            f'(on_board {"no" if is_power else "yes"}) '
            f'(dnp no) (uuid "{su}") {prop_txt} {pins} '
            f'(instances (project "{self.name}" (path "{path}" (reference "{p.ref}") (unit {p.unit})))))'
        )

    def _pin_item(self, p: Part, pin: Pin, net, ox: float, oy: float, path: str) -> str:
        px, py = _snap(ox + pin.x), _snap(oy - pin.y)
        uid = _uuid(path, p.ref, p.unit, "pin", pin.number)
        if net is NC:
            return f'(no_connect (at {_fmt(px)} {_fmt(py)}) (uuid "{uid}"))'
        angle = (pin.angle + 180) % 360
        justify = "right" if angle in (180, 270) else "left"
        if self.is_global(net):
            return (
                f'(global_label "{net}" (shape passive) (at {_fmt(px)} {_fmt(py)} {angle}) '
                f'(fields_autoplaced yes) {FONT.format(extra=f" (justify {justify})")} (uuid "{uid}") '
                f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {_fmt(px)} {_fmt(py)} 0) '
                f'{FONT.format(extra=" (hide yes)")}))'
            )
        return (
            f'(label "{net}" (at {_fmt(px)} {_fmt(py)} {angle}) (fields_autoplaced yes) '
            f'{FONT.format(extra=f" (justify {justify} bottom)")} (uuid "{uid}"))'
        )


def _unit_box(sym: LibSymbol, unit: int):
    pins = sym.unit_pins(unit)
    xs = [p.x for p in pins] + [sym.bbox[0], sym.bbox[2]] if pins else [sym.bbox[0], sym.bbox[2]]
    ys = [p.y for p in pins] + [sym.bbox[1], sym.bbox[3]] if pins else [sym.bbox[1], sym.bbox[3]]
    if pins:  # the library box spans all units; use this unit's pins plus a small body margin
        xs = [p.x for p in pins]
        ys = [p.y for p in pins]
        pad = 2.54
        return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    return min(xs), min(ys), max(xs), max(ys)


def write_project(root_path: Path, root_uuid: str, name: str, sheets: list[Sheet],
                  extra_libs: dict[str, Path]) -> list[Path]:
    project = Project(name, root_uuid, Libraries(extra_libs), sheets)
    return project.write(root_path)


__all__ = ["NC", "Sheet", "write_project"]
