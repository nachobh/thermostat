#!/usr/bin/env python3
"""Build the 84 x 84 mm Rev C thermostat board (Fritzing project).

Rev C = Rev B plus a 50-pin 0.5 mm FPC connector (J6, bottom side, facing the
display) so the DWIN DMG48480F040_01WTC(Z01) COF display plugs straight into
the board.  The display is mounted rotated 180 degrees (its FPC leaves through
the top edge, folds behind it and runs down to J6).  To make room for J6 the
relays move up 4.5 mm and the 230 V terminal and fuse move to the right-hand
column.  The NodeMCU is an Amica (22.86 mm rows) on sockets.  Every SELV
conductor is kept at least 8 mm from 230 V copper (validate_rev_b.py --design
build_rev_c_fzz).  An insulating sheet (>= 0.4 mm, V-0) must sit between the
PCB and the display, because the display FPC folds over the 230 V area.

All coordinates below are millimetres from the top-left board corner (y grows
downwards), as in Fritzing.  The schematic view uses net labels.
"""

from __future__ import annotations

import argparse
import heapq
import math
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape


DPI = 90.0
S = DPI / 25.4                      # px per mm
GRID = 3.0                          # px; 0.847 mm routing grid
BOARD_X, BOARD_Y = 100.0, 0.0       # px, board origin in the Fritzing scene
BOARD_W_MM = BOARD_H_MM = 84.0
BOARD_W, BOARD_H = BOARD_W_MM * S, BOARD_H_MM * S
TRACE_MILS = 24.0                   # SELV tracks, 0.61 mm
MAINS_TRACE_MM = 2.5                # 230 V tracks
SELV_MIN_Y_MM = 0.0                 # Rev C: SELV area comes from the distance to 230 V copper
MAINS_SELV_MM = 8.0                 # reinforced clearance (validator)
MAINS_MAINS_MM = 2.4                # functional clearance between 230 V nets
# The 230 V terminal now occupies the top-right corner, so that hole moves to (80, 38).
MOUNT_CENTERS_MM = ((4.0, 4.0), (80.0, 38.0), (4.0, 46.0), (80.0, 80.0))
MOUNT_DRILL_MM = 3.2
MOUNT_KEEPOUT_MM = 3.5
SKETCH = "thermostat_rev_c"
MAINS_NETS = {"L_IN", "L_FUSED", "OUT_COMP", "OUT_HEAT", "OUT_FAN"}


def px(x_mm: float, y_mm: float) -> tuple[float, float]:
    return BOARD_X + x_mm * S, BOARD_Y + y_mm * S


# --------------------------------------------------------------------------
# Single-stroke font for silkscreen text (Fritzing drops <text> in part SVGs).
# Glyphs live in a 4 x 6 box, y down.
# --------------------------------------------------------------------------

_O = [(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]
_P = [(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]
GLYPHS: dict[str, list[list[tuple[float, float]]]] = {
    "A": [[(0, 6), (0, 2), (2, 0), (4, 2), (4, 6)], [(0, 3.5), (4, 3.5)]],
    "B": [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)], [(0, 0), (3, 0), (4, 1), (4, 2), (3, 3)]],
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "D": [[(0, 0), (0, 6), (2.5, 6), (4, 4.5), (4, 1.5), (2.5, 0), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3), (2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    "J": [[(4, 0), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (0, 3.5)], [(1.2, 2.8), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [_O],
    "P": [_P],
    "Q": [_O, [(2.5, 4.5), (4, 6)]],
    "R": [_P, [(2, 3), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1, 6), (2, 3), (3, 6), (4, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    "0": [_O, [(0.5, 5), (3.5, 1)]],
    "1": [[(1, 1), (2, 0), (2, 6)], [(1, 6), (3, 6)]],
    "2": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (0, 6), (4, 6)]],
    "3": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)], [(1.5, 3), (3, 3)]],
    "4": [[(3, 6), (3, 0), (0, 4), (4, 4)]],
    "5": [[(4, 0), (0, 0), (0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]],
    "6": [[(3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]],
    "7": [[(0, 0), (4, 0), (1.5, 6)]],
    "8": [[(1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 2), (0, 1), (1, 0)],
          [(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3)]],
    "9": [[(4, 3), (1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6)]],
    "-": [[(0.5, 3), (3.5, 3)]],
    "+": [[(0.5, 3), (3.5, 3)], [(2, 1.5), (2, 4.5)]],
    ".": [[(1.7, 5.6), (2.3, 5.6), (2.3, 6), (1.7, 6), (1.7, 5.6)]],
    ":": [[(1.7, 1.6), (2.3, 1.6), (2.3, 2.2), (1.7, 2.2), (1.7, 1.6)],
          [(1.7, 5.4), (2.3, 5.4), (2.3, 6), (1.7, 6), (1.7, 5.4)]],
    "~": [[(0, 3.5), (1, 2.5), (2, 3.5), (3, 4.5), (4, 3.5)]],
    "/": [[(0, 6), (4, 0)]],
    "(": [[(2.5, 0), (1.5, 1.5), (1.5, 4.5), (2.5, 6)]],
    ")": [[(1.5, 0), (2.5, 1.5), (2.5, 4.5), (1.5, 6)]],
    "=": [[(0.5, 2), (3.5, 2)], [(0.5, 4), (3.5, 4)]],
    "!": [[(2, 0), (2, 4)], [(1.7, 5.4), (2.3, 5.4), (2.3, 6), (1.7, 6), (1.7, 5.4)]],
    ">": [[(0, 0), (4, 3), (0, 6)]],
    "<": [[(4, 0), (0, 3), (4, 6)]],
    "|": [[(2, -0.5), (2, 6.5)]],
    " ": [],
}


def text_strokes(text: str, x: float, y: float, height: float, anchor: str = "start"
                 ) -> list[list[tuple[float, float]]]:
    """Polylines (mm) for text whose top-left (or centre/end) is at x, y."""
    scale = height / 6.0
    advance = 5.4 * scale
    width = advance * len(text) - 1.4 * scale
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    lines = []
    for index, char in enumerate(text.upper()):
        for stroke in GLYPHS.get(char, [[(0, 0), (4, 0), (4, 6), (0, 6), (0, 0)]]):
            lines.append([(x + index * advance + gx * scale, y + gy * scale) for gx, gy in stroke])
    return lines


def text_width(text: str, height: float) -> float:
    return (5.4 * len(text) - 1.4) * height / 6.0


# --------------------------------------------------------------------------
# Footprints and schematic symbols
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Pad:
    name: str
    x: float
    y: float
    smd: bool = False
    drill: float = 0.0
    dia: float = 0.0
    w: float = 0.0
    h: float = 0.0
    sch_hidden: bool = False
    bottom: bool = False            # SMD pad on the bottom copper (part mounted underneath)


@dataclass
class Symbol:
    """Schematic symbol in 0.1 in units; pins as (pad index, x, y, side, label)."""
    width: int
    height: int
    pins: list[tuple[int, int, int, str, str]]
    drawing: str


@dataclass
class Footprint:
    key: str
    title: str
    label: str
    description: str
    pads: list[Pad]
    bodies: list[tuple[float, float, float, float]]
    silk: list[list[tuple[float, float]]] = field(default_factory=list)
    circles: list[tuple[float, float, float]] = field(default_factory=list)
    buses: list[list[int]] = field(default_factory=list)
    symbol: Symbol | None = None
    rotation: int = 0

    @property
    def smd(self) -> bool:
        return all(pad.smd for pad in self.pads)

    @property
    def bottom(self) -> bool:
        return all(pad.smd and pad.bottom for pad in self.pads)

    def bbox(self) -> tuple[float, float, float, float]:
        xs, ys = [], []
        for x0, y0, x1, y1 in self.bodies:
            xs += [x0, x1]
            ys += [y0, y1]
        for pad in self.pads:
            rx = pad.w / 2 if pad.smd else pad.dia / 2
            ry = pad.h / 2 if pad.smd else pad.dia / 2
            xs += [pad.x - rx, pad.x + rx]
            ys += [pad.y - ry, pad.y + ry]
        for line in self.silk:
            xs += [p[0] for p in line]
            ys += [p[1] for p in line]
        for cx, cy, r in self.circles:
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
        return min(xs) - 0.3, min(ys) - 0.3, max(xs) + 0.3, max(ys) + 0.3


def rotated(fp: Footprint, rotation: int) -> Footprint:
    """Rotate a footprint counter-clockwise (as seen from the top) in 90 degree steps."""
    if rotation % 360 == 0:
        return fp

    def turn(x: float, y: float) -> tuple[float, float]:
        for _ in range((rotation // 90) % 4):
            x, y = y, -x
        return x, y

    pads = []
    for pad in fp.pads:
        x, y = turn(pad.x, pad.y)
        w, h = (pad.h, pad.w) if (rotation // 90) % 2 else (pad.w, pad.h)
        pads.append(replace(pad, x=x, y=y, w=w, h=h))
    bodies = []
    for x0, y0, x1, y1 in fp.bodies:
        (ax, ay), (bx, by) = turn(x0, y0), turn(x1, y1)
        bodies.append((min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)))
    silk = [[turn(x, y) for x, y in line] for line in fp.silk]
    circles = [(*turn(cx, cy), r) for cx, cy, r in fp.circles]
    return replace(fp, key=f"{fp.key}_r{rotation}", pads=pads, bodies=bodies, silk=silk,
                   circles=circles, rotation=rotation)


def on_bottom(fp: Footprint) -> Footprint:
    """The same part mounted on the bottom side, in top-view board coordinates (mirrored in x)."""
    return replace(fp, key=f"{fp.key}_bot", pads=[replace(p, x=-p.x, bottom=True) for p in fp.pads],
                   bodies=[(-bx1, by0, -bx0, by1) for bx0, by0, bx1, by1 in fp.bodies],
                   silk=[[(-x, y) for x, y in line] for line in fp.silk],
                   circles=[(-cx, cy, r) for cx, cy, r in fp.circles])


def rect_lines(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def two_pin_symbol(kind: str, left: int, right: int, left_label: str = "", right_label: str = "") -> Symbol:
    body = {
        "res": '<path d="M1.5,1 L1.875,0.6 L2.375,1.4 L2.875,0.6 L3.375,1.4 L3.875,0.6 L4.375,1.4 L4.5,1" '
               'fill="none" stroke="#000000" stroke-width="0.1"/>',
        "cap": '<path d="M1.5,1 L2.8,1 M2.8,0.3 L2.8,1.7 M3.2,0.3 L3.2,1.7 M3.2,1 L4.5,1" '
               'fill="none" stroke="#000000" stroke-width="0.12"/>',
        "ecap": '<path d="M1.5,1 L2.8,1 M2.8,0.3 L2.8,1.7 M3.2,1 L4.5,1" fill="none" stroke="#000000" stroke-width="0.12"/>'
                '<path d="M3.45,0.3 Q3.15,1 3.45,1.7" fill="none" stroke="#000000" stroke-width="0.12"/>'
                '<path d="M2.1,0.35 L2.5,0.35 M2.3,0.15 L2.3,0.55" stroke="#000000" stroke-width="0.08"/>',
        "diode": '<path d="M1.5,1 L4.5,1" stroke="#000000" stroke-width="0.1"/>'
                 '<path d="M2.4,0.4 L2.4,1.6 L3.5,1 Z" fill="#000000"/>'
                 '<path d="M3.55,0.4 L3.55,1.6" stroke="#000000" stroke-width="0.14"/>',
        "fuse": '<rect x="1.8" y="0.65" width="2.4" height="0.7" fill="none" stroke="#000000" stroke-width="0.1"/>'
                '<path d="M1.5,1 L4.5,1" stroke="#000000" stroke-width="0.06"/>',
        "ptc": '<rect x="1.8" y="0.65" width="2.4" height="0.7" fill="none" stroke="#000000" stroke-width="0.1"/>'
               '<path d="M1.7,1.6 L2.3,1.6 L3.8,0.4 L4.3,0.4" fill="none" stroke="#000000" stroke-width="0.07"/>',
    }[kind]
    return Symbol(6, 2, [(left, 0, 1, "left", left_label), (right, 6, 1, "right", right_label)], body)


def box_symbol(title: str, left: list[tuple[int, str]], right: list[tuple[int, str]],
               width: int = 8, hidden: dict[int, int] | None = None) -> Symbol:
    """Rectangular symbol; `hidden` maps a hidden pad index onto a visible twin."""
    rows = max(len(left), len(right))
    height = rows + 2
    pins = []
    for row, (index, name) in enumerate(left):
        pins.append((index, 0, row + 1, "left", name))
    for row, (index, name) in enumerate(right):
        pins.append((index, width + 4, row + 1, "right", name))
    for twin_hidden, twin in (hidden or {}).items():
        pin = next(p for p in pins if p[0] == twin)
        pins.append((twin_hidden, pin[1], pin[2], "hidden", pin[4]))
    labels = []
    for index, x, y, side, name in pins:
        if side == "left":
            labels.append(f'<text x="2.3" y="{y + 0.25}" font-size="0.75" font-family="Droid Sans, sans-serif">{escape(name)}</text>')
        elif side == "right":
            labels.append(f'<text x="{width + 1.7}" y="{y + 0.25}" font-size="0.75" text-anchor="end" '
                          f'font-family="Droid Sans, sans-serif">{escape(name)}</text>')
    drawing = (f'<rect x="2" y="0.4" width="{width}" height="{height - 0.8}" fill="#fffbe8" stroke="#000000" stroke-width="0.1"/>'
               f'<text x="{2 + width / 2}" y="{height - 0.75}" font-size="0.8" text-anchor="middle" '
               f'font-family="Droid Sans, sans-serif" font-weight="bold">{escape(title)}</text>' + "".join(labels))
    return Symbol(width + 4, height, pins, drawing)


def fp_0805(label: str, kind: str) -> Footprint:
    pads = [Pad("1", -0.95, 0, smd=True, w=1.0, h=1.3), Pad("2", 0.95, 0, smd=True, w=1.0, h=1.3)]
    return Footprint(f"rb_0805_{kind}", f"0805 {kind}", label, "SMD 0805", pads,
                     [(-1.7, -0.9, 1.7, 0.9)], symbol=two_pin_symbol(kind, 0, 1))


def fp_sot23() -> Footprint:
    pads = [Pad("B", -1.0, -0.95, smd=True, w=1.2, h=0.7),
            Pad("E", -1.0, 0.95, smd=True, w=1.2, h=0.7),
            Pad("C", 1.0, 0.0, smd=True, w=1.2, h=0.7)]
    drawing = ('<circle cx="2.4" cy="2" r="1.35" fill="none" stroke="#000000" stroke-width="0.08"/>'
               '<path d="M1,2 L2,2 M2,1.2 L2,2.8 M2,1.6 L3,0.6 L3,0 M2,2.4 L3,3.4 L3,4" fill="none" stroke="#000000" stroke-width="0.1"/>'
               '<path d="M2.95,3.35 L2.45,3.25 L2.75,2.9 Z" fill="#000000"/>')
    symbol = Symbol(3, 4, [(0, 0, 2, "left", "B"), (2, 3, 0, "top", "C"), (1, 3, 4, "bottom", "E")],
                    '<path d="M0,2 L1,2" stroke="#000000" stroke-width="0.1"/>' + drawing)
    silk = [[(-0.25, -1.55), (0.6, -1.55)], [(-0.25, 1.55), (0.6, 1.55)]]
    return Footprint("rb_sot23_npn", "BC817-40 SOT-23 (1=B 2=E 3=C)", "Q", "SOT-23 NPN", pads,
                     [(-1.8, -1.6, 1.8, 1.6)], silk=silk, symbol=symbol)


def fp_sod123() -> Footprint:
    pads = [Pad("K", -1.65, 0, smd=True, w=0.9, h=1.2), Pad("A", 1.65, 0, smd=True, w=0.9, h=1.2)]
    silk = [[(-2.35, -0.75), (-2.35, 0.75)], [(-0.9, -0.85), (0.9, -0.85)], [(-0.9, 0.85), (0.9, 0.85)]]
    return Footprint("rb_sod123", "1N4148W SOD-123 (cathode bar = pad 1)", "D", "SOD-123 diode", pads,
                     [(-2.4, -0.95, 2.3, 0.95)], silk=silk, symbol=two_pin_symbol("diode", 1, 0, "A", "K"))


def fp_1812() -> Footprint:
    pads = [Pad("1", -2.15, 0, smd=True, w=1.3, h=3.4), Pad("2", 2.15, 0, smd=True, w=1.3, h=3.4)]
    return Footprint("rb_1812_ptc", "PTC 1812", "F", "SMD 1812 polyfuse", pads,
                     [(-3.0, -1.95, 3.0, 1.95)], symbol=two_pin_symbol("ptc", 0, 1))


def fp_jstxh(pins: int, names: list[str]) -> Footprint:
    width = 4.9 + 2.5 * (pins - 1)
    pads = [Pad(names[i], (i - (pins - 1) / 2) * 2.5, 0, drill=0.9, dia=1.8) for i in range(pins)]
    x0 = -width / 2
    silk = [rect_lines(x0 + 0.1, -3.3, -x0 - 0.1, 2.25), [(x0 + 0.1, -2.2), (x0 + 0.8, -2.2), (x0 + 0.8, -3.3)]]
    symbol = box_symbol(f"XH{pins}", [(i, f"{i + 1} {names[i]}") for i in range(pins)], [], width=7)
    return Footprint(f"rb_jstxh{pins}_{'_'.join(names).lower().replace('+', 'p')}", f"JST XH {pins}P B{pins}B-XH-A",
                     "J", "JST XH top entry, 2.50 mm, 0.90 mm drill", pads,
                     [(x0, -3.4, -x0, 2.35)], silk=silk, symbol=symbol)


def fp_mkds(pins: int, names: list[str], mains: bool) -> Footprint:
    pads = [Pad(names[i], (i - (pins - 1) / 2) * 5.08, 0, drill=1.3, dia=2.5) for i in range(pins)]
    half = 5.08 * pins / 2
    silk = [rect_lines(-half + 0.1, -4.8, half - 0.1, 4.8), [(-half + 0.1, -3.7), (-half + 1.2, -3.7), (-half + 1.2, -4.8)]]
    symbol = box_symbol(f"BORNA {pins}P", [(i, f"{i + 1} {names[i]}") for i in range(pins)], [], width=8)
    key = f"rb_mkds{pins}_{'mains' if mains else 'selv'}"
    return Footprint(key, f"Screw terminal {pins}P 5.08 mm", "J", "Phoenix MKDS 1,5 family, 1.30 mm drill",
                     pads, [(-half, -4.9, half, 4.9)], silk=silk, symbol=symbol)


def fp_tr5() -> Footprint:
    pads = [Pad("1", -2.54, 0, drill=1.0, dia=2.4), Pad("2", 2.54, 0, drill=1.0, dia=2.4)]
    return Footprint("rb_tr5", "TR5 fuse 5.08 mm", "F", "Radial TR5 fuse, 8.5 mm body", pads,
                     [(-4.25, -4.25, 4.25, 4.25)], circles=[(0, 0, 4.25)], symbol=two_pin_symbol("fuse", 0, 1))


def fp_radial_cap() -> Footprint:
    pads = [Pad("+", -1.25, 0, drill=0.8, dia=1.6), Pad("-", 1.25, 0, drill=0.8, dia=1.6)]
    silk = [[(-3.9, -1.6), (-3.1, -1.6)], [(-3.5, -2.0), (-3.5, -1.2)]]
    return Footprint("rb_radial63", "Electrolytic 6.3 mm, 2.5 mm pitch", "C", "Radial electrolytic", pads,
                     [(-3.15, -3.15, 3.15, 3.15)], silk=silk, circles=[(0, 0, 3.15)],
                     symbol=two_pin_symbol("ecap", 0, 1, "+", "-"))


RELAY_COIL_Y = 11.9   # coil pins relative to the relay body centre


def fp_relay() -> Footprint:
    """HF115F 1 pole 16 A, 5 mm pinning, top view; contacts towards -y."""
    d, dia = 1.3, 2.5
    pads = [
        Pad("A1", -3.78, RELAY_COIL_Y, drill=d, dia=dia), Pad("A2", 3.78, RELAY_COIL_Y, drill=d, dia=dia),
        Pad("NC", -3.78, RELAY_COIL_Y - 15.12, drill=d, dia=dia), Pad("NC'", 3.78, RELAY_COIL_Y - 15.12, drill=d, dia=dia, sch_hidden=True),
        Pad("COM", -3.78, RELAY_COIL_Y - 20.16, drill=d, dia=dia), Pad("COM'", 3.78, RELAY_COIL_Y - 20.16, drill=d, dia=dia, sch_hidden=True),
        Pad("NO", -3.78, RELAY_COIL_Y - 25.2, drill=d, dia=dia), Pad("NO'", 3.78, RELAY_COIL_Y - 25.2, drill=d, dia=dia, sch_hidden=True),
    ]
    silk = [rect_lines(-6.35, -14.5, 6.35, 14.5), [(-6.35, 9.0), (6.35, 9.0)]]
    symbol = box_symbol("HF115F 5V", [(0, "A1+"), (1, "A2-")], [(4, "COM"), (6, "NO"), (2, "NC")],
                        width=7, hidden={3: 2, 5: 4, 7: 6})
    return Footprint("rb_hf115f", "Hongfa HF115F/005-1ZS3 (16 A, 5 mm pinning)", "RL",
                     "SPDT 16 A 250 VAC relay, 5 V coil, 29 x 12.7 x 15.7 mm", pads,
                     [(-6.35, -14.5, 6.35, 14.5)], silk=silk, buses=[[2, 3], [4, 5], [6, 7]], symbol=symbol)


NODE_TOP = ["VIN", "GND", "RST", "EN", "3V3", "GND", "CLK", "SD0", "CMD", "SD1", "SD2", "SD3", "RSV", "RSV", "A0"]
NODE_BOTTOM = ["3V3", "GND", "TX", "RX", "D8", "D7", "D6", "D5", "GND", "3V3", "D4", "D3", "D2", "D1", "D0"]
NODE_ROW = 11.43                    # Amica v2: rows 22.86 mm apart


def node_pad(row: str, k: int) -> int:
    """Pad index in the NodeMCU footprint: T/B row, pin k (0 = USB end)."""
    return (0 if row == "T" else 15) + k


def fp_nodemcu() -> Footprint:
    pads = []
    for row, names, sign in (("T", NODE_TOP, -1), ("B", NODE_BOTTOM, 1)):
        for k, name in enumerate(names):
            pads.append(Pad(f"{row}{k:02d} {name}", (k - 7) * 2.54, sign * NODE_ROW, drill=1.0, dia=1.7))
    strip = 19.05
    bodies = [(-strip, -12.7, strip, -10.16), (-strip, 10.16, strip, 12.7)]
    silk = [rect_lines(-strip, -12.7, strip, -10.16), rect_lines(-strip, 10.16, strip, 12.7),
            [(-strip - 1.2, -1.5), (-strip - 1.2, 1.5)]]
    left = [(node_pad("T", k), NODE_TOP[k]) for k in range(15)]
    right = [(node_pad("B", k), NODE_BOTTOM[k]) for k in range(15)]
    symbol = box_symbol("NODEMCU AMICA", left, right, width=10)
    return Footprint("rc_nodemcu_amica", "NodeMCU Amica v2 socket (22.86 mm rows)", "U",
                     "Two 1x15 female headers, rows 0.9 in apart (NodeMCU Amica / v2, 48 x 25.4 mm)",
                     pads, bodies, silk=silk, symbol=symbol)


# FPC connector for the DWIN COF display: JUSHUO AFC07-S50ECA-00 (0.5 mm, 50 P, upper
# contact, H 2.0 mm), mounted on the BOTTOM side, opening towards -y (the display FPC comes
# down from the fold at the top edge).  Coordinates are top-view board coordinates; pin 1 is
# at +x because the display is rotated 180 degrees and seen through the board.
FPC_PIN1_X = 44.30                  # board x of pin 1 (pin 50 at 19.80)
# DWIN's STEP model: the FPC is 52.3 mm long from the LCD edge (2.14 mm inside the glass) and
# its tail spans 19.2-44.7 mm from the glass edge.  Folded flat behind the display (~3.5 mm used
# by the fold) its end reaches y ~ 50.9; J6 takes it with ~2 mm of slack.
FPC_PAD_Y = 49.70                   # board y of the pad row centre
FPC_GRID_MM = 3.0 / (90.0 / 25.4)    # routing grid in mm
FPC_FANOUT_Y = 61 * FPC_GRID_MM     # 51.65 mm, on the routing grid
FPC_LIVE = {1: "+5V", 2: "+5V", 3: "GND", 4: "GND", 5: "GND", 49: "TX2", 50: "RX2"}


def fp_fpc50() -> Footprint:
    """Footprint origin = centre of the pad row."""
    pads = []
    for k in range(1, 51):
        x = FPC_PIN1_X - (k - 1) * 0.5 - (FPC_PIN1_X - 12.25)
        pads.append(Pad(str(k), x, 0.0, smd=True, w=0.3, h=1.2, bottom=True,
                        sch_hidden=k not in FPC_LIVE))
    # Fitting nails (mechanical, unconnected) on the insertion side.
    for name, x in (("MP1", 13.85), ("MP2", -13.85)):
        pads.append(Pad(name, x, -2.17, smd=True, w=2.2, h=3.3, bottom=True, sch_hidden=True))
    # Fan-out pads where the router picks up the four used signals.
    dy = FPC_FANOUT_Y - FPC_PAD_Y
    fan = {"F5V": 55 * FPC_GRID_MM, "FGND": 49 * FPC_GRID_MM, "FTX": 27 * FPC_GRID_MM, "FRX": 21 * FPC_GRID_MM}
    for name, bx in fan.items():
        pads.append(Pad(name, bx - (FPC_PIN1_X - 12.25), dy, smd=True, w=0.8, h=0.8, bottom=True, sch_hidden=True))
    silk = [rect_lines(-15.3, -6.5, 15.3, 0.9), [(13.0, 1.4), (13.6, 1.4)]]
    live = [(k - 1, f"{k} {FPC_LIVE[k]}") for k in sorted(FPC_LIVE)]
    hidden = {i: 0 for i, pad in enumerate(pads) if pad.sch_hidden}
    symbol = box_symbol("DWIN FPC50", live, [], width=8, hidden=hidden)
    return Footprint("rc_fpc50_afc07_bottom", "FPC 0.5 mm 50P upper contact (AFC07-S50ECA-00), bottom side", "J",
                     "JUSHUO AFC07-S50ECA-00, slide lock, H 2.0 mm; mounted on the bottom side",
                     pads, [(-15.3, -6.5, 15.3, 0.9)], silk=silk, symbol=symbol)


# --------------------------------------------------------------------------
# Placement (mm, part origin) and bill of materials data
# --------------------------------------------------------------------------

@dataclass
class Part:
    ref: str
    fp: Footprint
    x: float
    y: float
    value: str
    bom: dict[str, str]
    sch: tuple[int, int]            # schematic position, 0.1 in units
    dnp: bool = False


RELAY_COIL_ROW = 38.5               # Rev B: 43.0; moved up to free the FPC connector area
RELAY_Y = RELAY_COIL_ROW - RELAY_COIL_Y
RELAY_X = (27.0, 42.0, 57.0)
NODE_X, NODE_Y = 31.78, 67.13       # rows at y 55.70 and 78.56 (room for the J6 fan-out)
NODE_MODULE_MM = (NODE_X - 24.15, NODE_Y - 12.7, NODE_X + 24.15, NODE_Y + 12.7)   # Amica 48.3 x 25.4
J20_X, J20_Y = 76.5, 11.02          # vertical; pads at y 3.40 / 8.48 / 13.56 / 18.64
F2_X, F2_Y = 76.5, 26.54            # vertical; pads at y 24.00 / 29.08

# All SMD parts sit on the bottom side (facing the display) next to J6, so SMT assembly is
# one-sided.  Seen from the top they are mirrored; the base footprints are chosen so that the
# driver channel keeps its straight base and ground lines after mirroring.
R_0805 = on_bottom(fp_0805("R", "res"))
R_BASE = on_bottom(rotated(fp_0805("R", "res"), 180))     # pad 1 (GPIO) on the left
R_PULL = on_bottom(rotated(fp_0805("R", "res"), 90))      # vertical, pad 1 (base) at the bottom
C_0805 = on_bottom(fp_0805("C", "cap"))
DIODE = on_bottom(fp_sod123())                            # anode on the left, next to the transistor
NPN = on_bottom(rotated(fp_sot23(), 180))                 # B (lower) and E (upper) on the left, C right

BOM_INFO = {
    "relay": {"mpn": "HF115F/005-1ZS3", "mfr": "Hongfa", "lcsc": "C9225", "type": "THT",
              "desc": "Relay SPDT 16 A 250 VAC, 5 V coil 62 ohm (variant ...AF with AgSnO2 also fits)"},
    "mains_terminal": {"mpn": "1715747 (MKDS 1,5/4-5,08)", "mfr": "Phoenix Contact", "lcsc": "", "type": "THT",
                       "desc": "Screw terminal 4P 5.08 mm 250 V 17.5 A (230 V side: COMP, VENT, CALOR, L)"},
    "fuse": {"mpn": "37416300000 (TR5 T6.3A)", "mfr": "Littelfuse", "lcsc": "", "type": "THT",
             "desc": "Fuse TR5 time-lag 6.3 A 250 VAC, 5.08 mm (alt. Schurter MST 250 0034.6623)"},
    "power_terminal": {"mpn": "1715721 (MKDS 1,5/2-5,08)", "mfr": "Phoenix Contact", "lcsc": "C480516", "type": "THT",
                       "desc": "Screw terminal 2P 5.08 mm, 5 V input"},
    "xh2": {"mpn": "B2B-XH-A(LF)(SN)", "mfr": "JST", "lcsc": "C158012", "type": "THT", "desc": "JST XH 2P vertical"},
    "xh3": {"mpn": "B3B-XH-A(LF)(SN)", "mfr": "JST", "lcsc": "C144394", "type": "THT", "desc": "JST XH 3P vertical"},
    "xh4": {"mpn": "B4B-XH-A(LF)(SN)", "mfr": "JST", "lcsc": "C144395", "type": "THT", "desc": "JST XH 4P vertical"},
    "socket15": {"mpn": "1x15 female header 2.54 mm, 8.5 mm", "mfr": "generic", "lcsc": "", "type": "THT",
                 "desc": "NodeMCU Amica socket: 2 pcs, rows 22.86 mm apart"},
    "fpc50": {"mpn": "AFC07-S50ECA-00", "mfr": "JUSHUO", "lcsc": "C262650", "type": "SMD",
              "desc": "FPC connector 0.5 mm 50P, upper contact, slide lock, H 2.0 mm - BOTTOM SIDE"},
    "npn": {"mpn": "BC817-40", "mfr": "Shandong Jingdao", "lcsc": "C2982853", "type": "SMD",
            "desc": "NPN 45 V 500 mA hFE 250-600, SOT-23"},
    "diode": {"mpn": "1N4148W", "mfr": "Changjiang", "lcsc": "C81598", "type": "SMD", "desc": "Diode 100 V 150 mA SOD-123"},
    "r1k": {"mpn": "0805W8F1001T5E", "mfr": "UNI-ROYAL", "lcsc": "C17513", "type": "SMD", "desc": "Resistor 1 kohm 1% 0805"},
    "r10k": {"mpn": "0805W8F1002T5E", "mfr": "UNI-ROYAL", "lcsc": "C17414", "type": "SMD", "desc": "Resistor 10 kohm 1% 0805"},
    "c100n": {"mpn": "CL21B104KBCNNNC", "mfr": "Samsung", "lcsc": "C49678", "type": "SMD", "desc": "Capacitor 100 nF 50 V X7R 0805"},
    "c220u": {"mpn": "CJ221MD711B3", "mfr": "TWBOR", "lcsc": "C2886738", "type": "THT",
              "desc": "Electrolytic 220 uF 16 V 6.3 x 11 mm, 2.5 mm"},
    "ptc": {"mpn": "1812L110/16DR", "mfr": "Littelfuse", "lcsc": "C142746", "type": "SMD",
            "desc": "PTC resettable 1.1 A hold 16 V 1812"},
}

PARTS: list[Part] = []


def add(ref, fp, x, y, value, bom_key, sch, dnp=False):
    PARTS.append(Part(ref, fp, x, y, value, BOM_INFO[bom_key], sch, dnp))


# 230 V side.  Relay functions (Rev C): RL1 compressor, RL2 fan, RL3 heating (shortest run).
add("J20", rotated(fp_mkds(4, ["L", "CALOR", "VENT", "COMP"], True), 90), J20_X, J20_Y, "MKDS 4P 230V",
    "mains_terminal", (0, 0))
add("F2", rotated(fp_tr5(), 90), F2_X, F2_Y, "T6.3A 250V", "fuse", (22, 2))
for index, (name, x) in enumerate(zip(("COMP", "FAN", "HEAT"), RELAY_X), start=1):
    add(f"RL{index}", fp_relay(), x, RELAY_Y, f"HF115F 5V {name}", "relay", (44 + 28 * (index - 1), 0))

# SELV side.
add("U1", fp_nodemcu(), NODE_X, NODE_Y, "NodeMCU Amica", "socket15", (0, 24))
add("J6", fp_fpc50(), FPC_PIN1_X - 12.25, FPC_PAD_Y, "DWIN FPC50", "fpc50", (0, 46))
for index, (name, y) in enumerate((("COMP", 45.6), ("FAN", 50.8), ("HEAT", 56.0))):
    r_base, r_pull, q, d = 2 * index + 1, 2 * index + 2, index + 1, index + 1
    sy = 24 + index * 10
    # Base resistor, vertical pull-down and the transistor's B/E pins share two straight lines.
    add(f"R{r_base}", R_BASE, 52.6, y + 0.95, "1k", "r1k", (36, sy))
    add(f"R{r_pull}", R_PULL, 55.2, y, "10k", "r10k", (36, sy + 4))
    add(f"Q{q}", NPN, 58.0, y, "BC817-40", "npn", (60, sy))
    add(f"D{d}", DIODE, 62.7, y, "1N4148W", "diode", (76, sy))
add("J1", fp_mkds(2, ["+5V", "GND"], False), 75.6, 53.5, "5V IN", "power_terminal", (112, 24))
add("F1", on_bottom(fp_1812()), 76.5, 44.5, "1.1A PTC", "ptc", (132, 24))
add("C1", fp_radial_cap(), 68.5, 44.5, "220uF 16V", "c220u", (132, 29))
add("C2", C_0805, 67.2, 49.9, "100nF", "c100n", (132, 34))
add("J5", fp_jstxh(4, ["3V3", "GND", "SCL", "SDA"]), 75.0, 71.0, "RTC I2C", "xh4", (112, 38))
# Temperature/humidity: Sensirion SHT40 module on the I2C bus (shared with the RTC), outside the case.
add("J3", fp_jstxh(4, ["3V3", "GND", "SCL", "SDA"]), 70.0, 79.0, "SHT40", "xh4", (112, 46))
add("C3", C_0805, 58.5, 71.0, "100nF", "c100n", (132, 39))
for ref, y, value, key, sch in (("R16", 58.7, "10k", "r10k", (36, 58)), ("R18", 61.3, "1k", "r1k", (60, 58)),
                                ("R17", 63.9, "10k", "r10k", (36, 62)), ("R19", 66.5, "1k", "r1k", (60, 62))):
    add(ref, R_0805, 44.5, y, value, key, sch)

PART_BY_REF = {part.ref: part for part in PARTS}


def pad_index(ref: str, name: str) -> int:
    pads = PART_BY_REF[ref].fp.pads
    for index, pad in enumerate(pads):
        if pad.name == name:
            return index
    raise KeyError(f"{ref} has no pad {name}")


def T(ref: str, name: str) -> tuple[str, int]:
    return ref, pad_index(ref, name)


def NODE(row: str, k: int) -> list[tuple[str, int]]:
    return [("U1", node_pad(row, k))]


# SELV nets (auto-routed).  Order inside each list: first terminal seeds the tree.
NETS: dict[str, list[tuple[str, int]]] = {
    "5V_IN": [T("J1", "+5V"), T("F1", "1")],
    "5V": [T("F1", "2"), T("C1", "+"), T("C2", "1"), T("D1", "K"), T("D2", "K"), T("D3", "K"),
           T("RL3", "A1"), T("RL2", "A1"), T("RL1", "A1"), *NODE("T", 0), T("J6", "F5V")],
    "GND": [T("J1", "GND"), T("C1", "-"), T("C2", "2"), T("Q1", "E"), T("Q2", "E"), T("Q3", "E"),
            T("R2", "2"), T("R4", "2"), T("R6", "2"), *NODE("B", 8), *NODE("T", 1),
            T("J5", "GND"), T("J3", "GND"), T("C3", "2"), T("J6", "FGND")],
    "3V3": [*NODE("B", 9), T("C3", "1"), T("J3", "3V3"), T("J5", "3V3"),
            T("R16", "2"), T("R17", "2")],
    "D1_SCL": [*NODE("B", 13), T("J5", "SCL"), T("J3", "SCL")],
    "D2_SDA": [*NODE("B", 12), T("J5", "SDA"), T("J3", "SDA")],
    "D3_RXD": [*NODE("B", 11), T("R16", "1"), T("R18", "1")],
    "DWIN_TX": [T("R18", "2"), T("J6", "FTX")],
    "D4_TXD": [*NODE("B", 10), T("R17", "1"), T("R19", "1")],
    "DWIN_RX": [T("R19", "2"), T("J6", "FRX")],
    "D7_COMP": [*NODE("B", 5), T("R1", "1")],
    "D6_FAN": [*NODE("B", 6), T("R3", "1")],
    "D8_HEAT": [*NODE("B", 4), T("R5", "1")],
    "BASE_COMP": [T("R1", "2"), T("R2", "1"), T("Q1", "B")],
    "BASE_FAN": [T("R3", "2"), T("R4", "1"), T("Q2", "B")],
    "BASE_HEAT": [T("R5", "2"), T("R6", "1"), T("Q3", "B")],
    "COIL_COMP": [T("Q1", "C"), T("D1", "A"), T("RL1", "A2")],
    "COIL_FAN": [T("Q2", "C"), T("D2", "A"), T("RL2", "A2")],
    "COIL_HEAT": [T("Q3", "C"), T("D3", "A"), T("RL3", "A2")],
}

def pad_mm(ref: str, index: int) -> tuple[float, float]:
    part = PART_BY_REF[ref]
    pad = part.fp.pads[index]
    return part.x + pad.x, part.y + pad.y


def _p(ref, name):
    return pad_mm(*T(ref, name))


# Hand-drawn SELV fan-out of the 0.5 mm FPC pins: net -> (terminals, [(layer, width, points)]).
FPC_TRACE_MM = 0.25


def _fpc(k):
    return FPC_PIN1_X - (k - 1) * 0.5, FPC_PAD_Y


def fpc_fanout() -> dict[str, tuple[list[tuple[str, int]], list[tuple[str, float, list[tuple[float, float]]]]]]:
    y = FPC_FANOUT_Y
    p = {k: _fpc(k) for k in FPC_LIVE}
    fan = {n: pad_mm(*T("J6", n)) for n in ("F5V", "FGND", "FTX", "FRX")}
    w = FPC_TRACE_MM
    return {
        "5V": ([T("J6", "1"), T("J6", "2"), T("J6", "F5V")],
               [("bottom", w, [p[1], (p[1][0], y)]), ("bottom", w, [p[2], (p[2][0], y), (p[1][0], y), fan["F5V"]])]),
        "GND": ([T("J6", "3"), T("J6", "4"), T("J6", "5"), T("J6", "FGND")],
                [("bottom", w, [p[3], (p[3][0], y)]), ("bottom", w, [p[4], (p[4][0], y)]),
                 ("bottom", w, [p[5], (p[5][0], y)]),
                 ("bottom", w, [(p[3][0], y), (p[4][0], y), (p[5][0], y), fan["FGND"]])]),
        "DWIN_TX": ([T("J6", "49"), T("J6", "FTX")], [("bottom", w, [p[49], (p[49][0], y), fan["FTX"]])]),
        "DWIN_RX": ([T("J6", "50"), T("J6", "FRX")], [("bottom", w, [p[50], (p[50][0], y), fan["FRX"]])]),
    }


MANUAL_NETS_TERMINALS = {net: terminals for net, (terminals, _) in fpc_fanout().items()}

# 230 V nets: hand-drawn tracks, (layer, [points mm]).
MAINS_NETS_TERMINALS: dict[str, list[tuple[str, int]]] = {
    "L_IN": [T("J20", "L"), T("F2", "2")],
    "L_FUSED": [T("F2", "1")] + [T(f"RL{i}", n) for i in (3, 2, 1) for n in ("COM'", "COM")],
    "OUT_COMP": [T("J20", "COMP"), T("RL1", "NO"), T("RL1", "NO'")],
    "OUT_FAN": [T("J20", "VENT"), T("RL2", "NO"), T("RL2", "NO'")],
    "OUT_HEAT": [T("J20", "CALOR"), T("RL3", "NO"), T("RL3", "NO'")],
}
MAINS_NETS = set(MAINS_NETS_TERMINALS)
MAINS_WIDTH = {"OUT_FAN": 2.0}      # the fan run passes 4.8 mm from the RL3 contacts


def mains_paths() -> dict[str, list[tuple[str, list[tuple[float, float]]]]]:
    j_l, j_c, j_v, j_h = (_p("J20", n) for n in ("L", "COMP", "VENT", "CALOR"))
    f_1, f_2 = _p("F2", "1"), _p("F2", "2")
    com = [(_p(f"RL{i}", "COM'"), _p(f"RL{i}", "COM")) for i in (3, 2, 1)]
    no = [(_p(f"RL{i}", "NO"), _p(f"RL{i}", "NO'")) for i in (1, 2, 3)]
    bus_x = 66.0
    bus = [f_1, (bus_x, f_1[1]), (bus_x, com[0][0][1])] + [q for pair in com for q in pair]
    return {
        "L_IN": [("top", [j_l, f_2])],
        "L_FUSED": [("bottom", bus)],
        # Compressor: over the top of RL2 and RL3 at the COMP pad height.
        "OUT_COMP": [("top", [no[0][0], no[0][1]]), ("top", [no[0][1], (no[0][1][0], j_c[1]), j_c])],
        # Fan: between the compressor run and the RL3 contacts.
        "OUT_FAN": [("top", [no[1][0], no[1][1]]), ("top", [no[1][1], (no[1][1][0], j_v[1]), j_v])],
        # Heating: straight to the right from RL3.
        "OUT_HEAT": [("top", [no[2][0], no[2][1]]), ("top", [no[2][1], (j_h[0] - 3.0, no[2][1][1]), j_h])],
    }


# --------------------------------------------------------------------------
# Fritzing part assets
# --------------------------------------------------------------------------

def silk_svg(lines, circles, ox, oy, width=0.18) -> str:
    out = []
    for line in lines:
        d = " ".join(("M" if i == 0 else "L") + f"{x - ox:.3f},{y - oy:.3f}" for i, (x, y) in enumerate(line))
        out.append(f'<path d="{d}" fill="none" stroke="#f0f0f0" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')
    for cx, cy, r in circles:
        out.append(f'<circle cx="{cx - ox:.3f}" cy="{cy - oy:.3f}" r="{r:.3f}" fill="none" stroke="#f0f0f0" stroke-width="{width}"/>')
    return "".join(out)


def mirrored_x(fp: Footprint) -> Footprint:
    """Fritzing flips a bottom-side part left-right about its SVG centre; pre-mirror it about that centre."""
    x0, _, x1, _ = fp.bbox()
    m = x0 + x1
    return replace(fp, pads=[replace(p, x=m - p.x) for p in fp.pads],
                   bodies=[(m - bx1, by0, m - bx0, by1) for bx0, by0, bx1, by1 in fp.bodies],
                   silk=[[(m - x, y) for x, y in line] for line in fp.silk],
                   circles=[(m - cx, cy, r) for cx, cy, r in fp.circles])



def footprint_assets(fp: Footprint) -> dict[str, str]:
    if fp.bottom:
        fp = mirrored_x(fp)
    x0, y0, x1, y1 = fp.bbox()
    w, h = x1 - x0, y1 - y0
    pads_svg = []
    for n, pad in enumerate(fp.pads):
        if pad.smd:
            pads_svg.append(f'<rect id="connector{n}pad" x="{pad.x - pad.w / 2 - x0:.4f}" y="{pad.y - pad.h / 2 - y0:.4f}" '
                            f'width="{pad.w:.4f}" height="{pad.h:.4f}" fill="#f7bd13" stroke="none"/>')
        else:
            r = (pad.dia + pad.drill) / 4
            stroke = (pad.dia - pad.drill) / 2
            pads_svg.append(f'<circle id="connector{n}pad" cx="{pad.x - x0:.4f}" cy="{pad.y - y0:.4f}" r="{r:.4f}" '
                            f'fill="none" stroke="#f7bd13" stroke-width="{stroke:.4f}"/>')
    copper = "".join(pads_svg)
    head = (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
            f'baseProfile="tiny" width="{w:.4f}mm" height="{h:.4f}mm" viewBox="0 0 {w:.4f} {h:.4f}">')
    silk = silk_svg(fp.silk, fp.circles, x0, y0)
    if fp.smd:
        pcb = f'{head}<g id="copper1">{copper}</g><g id="silkscreen">{silk}</g></svg>'
    else:
        pcb = f'{head}<g id="copper1">{copper}<g id="copper0">{copper}</g></g><g id="silkscreen">{silk}</g></svg>'

    pins_bb = "".join(
        f'<rect id="connector{n}pin" x="{pad.x - x0 - 0.3:.3f}" y="{pad.y - y0 - 0.3:.3f}" width="0.6" height="0.6" fill="#777"/>'
        for n, pad in enumerate(fp.pads))
    breadboard = (f'{head}<g id="breadboard"><rect x="0" y="0" width="{w:.3f}" height="{h:.3f}" fill="#2a6b45"/>{pins_bb}</g></svg>')
    icon = f'{head}<g id="icon"><rect x="0" y="0" width="{w:.3f}" height="{h:.3f}" fill="#2a6b45"/></g></svg>'

    sym = fp.symbol
    sw, sh = sym.width, sym.height
    pin_svg = []
    for index, x, y, side, _ in sym.pins:
        if side == "hidden":
            pin_svg.append(f'<rect id="connector{index}pin" x="{x - 0.05}" y="{y - 0.05}" width="0.1" height="0.1" fill="none"/>'
                           f'<rect id="connector{index}terminal" x="{x}" y="{y}" width="0.0001" height="0.0001" fill="none"/>')
            continue
        if side == "left":
            line, term = (x, y, x + 2, y), (x, y)
        elif side == "right":
            line, term = (x - 2, y, x, y), (x, y)
        elif side == "top":
            line, term = (x, y, x, y + 1), (x, y)
        else:
            line, term = (x, y - 1, x, y), (x, y)
        if sym.width == 6 and side in ("left", "right"):     # two-pin symbols draw their own leads
            line = (x, y, x + 1.5, y) if side == "left" else (x - 1.5, y, x, y)
        pin_svg.append(f'<line id="connector{index}pin" x1="{line[0]}" y1="{line[1]}" x2="{line[2]}" y2="{line[3]}" '
                       f'stroke="#555" stroke-width="0.1"/>'
                       f'<rect id="connector{index}terminal" x="{term[0]}" y="{term[1]}" width="0.0001" height="0.0001" fill="none"/>')
    schematic = (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
                 f'baseProfile="tiny" width="{sw / 10}in" height="{sh / 10}in" viewBox="0 0 {sw} {sh}">'
                 f'<g id="schematic">{sym.drawing}{"".join(pin_svg)}</g></svg>')

    connectors = []
    for n, pad in enumerate(fp.pads):
        pcb_p = ('<p layer="copper1" svgId="connector{n}pad"/>' if pad.smd else
                 '<p layer="copper0" svgId="connector{n}pad"/><p layer="copper1" svgId="connector{n}pad"/>').format(n=n)
        hybrid = ' hybrid="yes"' if pad.sch_hidden else ""
        connectors.append(
            f'<connector id="connector{n}" name="{escape(pad.name)}" type="male"><description>{escape(pad.name)}</description><views>'
            f'<breadboardView><p layer="breadboard" svgId="connector{n}pin"/></breadboardView>'
            f'<schematicView><p layer="schematic" svgId="connector{n}pin" terminalId="connector{n}terminal"{hybrid}/></schematicView>'
            f'<pcbView>{pcb_p}</pcbView></views></connector>')
    buses = "".join(f'<bus id="bus{i}">' + "".join(f'<nodeMember connectorId="connector{m}"/>' for m in members) + "</bus>"
                    for i, members in enumerate(fp.buses))
    layers = '<layer layerId="copper1"/><layer layerId="silkscreen"/>' + ("" if fp.smd else '<layer layerId="copper0"/>')
    base = fp.key
    fzp = (f'<?xml version="1.0" encoding="UTF-8"?>\n<module fritzingVersion="1.0.1" moduleId="{module_id(fp)}">'
           f'<version>1</version><author>thermostat project</author><title>{escape(fp.title)}</title>'
           f'<label>{fp.label}</label><description>{escape(fp.description)}</description>'
           f'<properties><property name="family">thermostat rev b</property>'
           f'<property name="package">{"SMD" if fp.smd else "THT"}</property></properties><views>'
           f'<iconView><layers image="icon/{base}_icon.svg"><layer layerId="icon"/></layers></iconView>'
           f'<breadboardView><layers image="breadboard/{base}_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>'
           f'<schematicView><layers image="schematic/{base}_schematic.svg"><layer layerId="schematic"/></layers></schematicView>'
           f'<pcbView><layers image="pcb/{base}_pcb.svg">{layers}</layers></pcbView></views>'
           f'<connectors>{"".join(connectors)}</connectors>' + (f"<buses>{buses}</buses>" if buses else "") + "</module>")
    return {"fzp": fzp, "pcb": pcb, "breadboard": breadboard, "icon": icon, "schematic": schematic}


def module_id(fp: Footprint) -> str:
    return "ThermostatRevB_" + fp.key


MOUNT_FZP = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="ThermostatRevBMount">
 <version>1</version><author>thermostat project</author>
 <title>Mounting hole NPTH {MOUNT_DRILL_MM} mm</title><label>H</label>
 <description>Unplated mounting hole; use nylon M3 screws.</description>
 <properties><property name="family">mounting hole</property><property name="package">NPTH</property></properties>
 <views><iconView><layers image="icon/rb_mount_icon.svg"><layer layerId="icon"/></layers></iconView>
 <pcbView><layers image="pcb/rb_mount_pcb.svg"><layer layerId="copper1"/>
  <layer layerId="copper0"/><layer layerId="silkscreen"/></layers></pcbView></views>
 <connectors></connectors>
</module>'''
MOUNT_PCB_SVG = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" width="7mm" height="7mm" viewBox="0 0 7 7">
 <g id="copper1"><g id="copper0"><circle id="nonconn0" cx="3.5" cy="3.5" r="{MOUNT_DRILL_MM / 2}" fill="#000000"/></g></g>
 <g id="silkscreen"><circle cx="3.5" cy="3.5" r="3.25" fill="none" stroke="#f0f0f0" stroke-width="0.2"/></g>
</svg>'''
MOUNT_ICON_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="7mm" height="7mm" viewBox="0 0 7 7"><g id="icon">
<circle cx="3.5" cy="3.5" r="2.8" fill="none" stroke="#888" stroke-width="0.4"/></g></svg>'''

VIA_PCB_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" width="1.4mm" height="1.4mm" viewBox="0 0 1.4 1.4">
  <g id="copper1"><circle id="connector0pad" cx="0.7" cy="0.7" r="0.5" fill="none" stroke="#f7bd13" stroke-width="0.4"/>
    <g id="copper0"><circle id="connector0pad" cx="0.7" cy="0.7" r="0.5" fill="none" stroke="#f7bd13" stroke-width="0.4"/></g>
  </g></svg>"""
VIA_ICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1.4mm" height="1.4mm" viewBox="0 0 1.4 1.4"><g id="icon">
<circle cx="0.7" cy="0.7" r="0.6" fill="#d9a400"/></g></svg>"""
VIA_FZP = """<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="ThermostatRevBVia"><version>1</version><author>thermostat project</author>
<title>Plated via 1.4/0.6 mm</title><label>V</label><description>Two-layer plated through via.</description>
<properties><property name="family">via</property><property name="package">THT</property></properties>
<views><iconView><layers image="icon/rb_via_icon.svg"><layer layerId="icon"/></layers></iconView>
<pcbView><layers image="pcb/rb_via_pcb.svg"><layer layerId="copper1"/><layer layerId="copper0"/></layers></pcbView></views>
<connectors><connector id="connector0" name="via" type="male"><description>via</description>
<views><pcbView><p layer="copper0" svgId="connector0pad"/><p layer="copper1" svgId="connector0pad"/></pcbView></views>
</connector></connectors></module>"""


def board_silk() -> tuple[list[list[tuple[float, float]]], list[tuple[float, float, float]]]:
    """Board-level silkscreen in board mm."""
    lines: list[list[tuple[float, float]]] = []

    def text(s, x, y, h=1.2, anchor="start"):
        lines.extend(text_strokes(s, x, y, h, anchor))

    # Zone boundary (dashed) between 230 V and SELV.
    y = 34.2
    x = 1.0
    while x < 83.0:
        lines.append([(x, y), (min(x + 1.6, 83.0), y)])
        x += 2.6
    text("! PELIGRO 230V~", 2.5, 12.0, 1.0)
    text("NO TOCAR", 2.5, 14.0, 1.0)
    text("TERMOSTATO", 2.5, 19.0, 1.1)
    text("REV C 84X84", 2.5, 21.2, 1.1)
    text("2026-10", 2.5, 23.4, 1.1)
    text("SELV 5V", 2.5, 35.4, 1.1)
    for label, yy in (("COMP(4)", 3.4), ("VENT(3)", 8.48), ("CALOR(1)", 13.56), ("L", 18.64)):
        text(label, 71.0, yy - 0.5, 1.0, "end")
    text("J20", 76.5, 22.0 - 0.3, 0.9, "middle")
    text("F2", 70.6, 25.6, 1.0, "end")
    text("T6.3A", 70.6, 27.6, 1.0, "end")
    for index, (name, x) in enumerate(zip(("COMP", "VENT", "CALOR"), RELAY_X), start=1):
        text(f"RL{index}", x, RELAY_Y + 3.6, 1.2, "middle")
        text(name, x, RELAY_Y + 5.6, 1.0, "middle")
        text("NC", x, RELAY_Y - 3.22 - 0.45, 0.9, "middle")
        text("COM", x, RELAY_Y - 8.26 - 0.45, 0.9, "middle")
        text("NO", x, RELAY_Y - 13.3 - 0.45, 0.9, "middle")
    # Connector legends.
    text("+5V GND", 75.6, 59.0, 1.0, "middle")
    text("J1 5V", 82.6, 48.0, 0.9, "end")
    text("J5 RTC 3V3 G SCL SDA", 75.0, 74.6, 0.9, "middle")
    text("J3 SHT40 I2C", 70.0, 82.5, 0.9, "middle")
    text("USB", 2.0, 61.6, 1.0)
    text("U1 NODEMCU AMICA", NODE_X, NODE_Y - 0.6, 1.2, "middle")
    text("VIN", 14.0, NODE_Y - NODE_ROW - 2.6, 0.8, "middle")
    text("J6 FPC (CARA INF.)", NODE_X, 42.8, 0.9, "middle")
    text("C1", PART_BY_REF["C1"].x, PART_BY_REF["C1"].y + 3.6, 0.9, "middle")
    text("SMD: CARA INFERIOR", 66.0, 61.0, 0.9)
    return lines, []


def bottom_silk() -> list[list[tuple[float, float]]]:
    """Bottom silkscreen (board top-view mm): part outlines and mirrored reference designators."""
    lines: list[list[tuple[float, float]]] = []
    for part in PARTS:
        if not part.fp.bottom:
            continue
        lines += [[(part.x + x, part.y + y) for x, y in line] for line in part.fp.silk]
        x0, y0, x1, y1 = part.fp.bodies[0]
        h = 0.8
        if part.ref == "J6":
            tx, ty = part.x, part.y + y0 - 1.6
        elif part.ref.startswith(("R16", "R17", "R18", "R19")):
            tx, ty = part.x + x1 + 1.6, part.y - h / 2
        else:
            tx, ty = part.x, part.y + y0 - 1.2
        strokes = text_strokes(part.ref, tx, ty, h, "middle")
        lines += [[(2 * tx - x, y) for x, y in stroke] for stroke in strokes]     # mirrored: read from below
    return lines


def board_silk_assets() -> dict[str, str]:
    lines, circles = board_silk()
    head = (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
            f'baseProfile="tiny" width="{BOARD_W_MM}mm" height="{BOARD_H_MM}mm" viewBox="0 0 {BOARD_W_MM} {BOARD_H_MM}">')
    pcb = f'{head}<g id="silkscreen">{silk_svg(lines, circles, 0, 0, 0.16)}</g></svg>'
    icon = f'{head}<g id="icon"><rect width="10" height="10" fill="#ccc"/></g></svg>'
    fzp = '''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="ThermostatRevBSilk"><version>1</version><author>thermostat project</author>
<title>Rev B board legend</title><label>LOGO</label><description>Board-level silkscreen legend.</description>
<properties><property name="family">silkscreen</property></properties>
<views><iconView><layers image="icon/rb_silk_icon.svg"><layer layerId="icon"/></layers></iconView>
<pcbView><layers image="pcb/rb_silk_pcb.svg"><layer layerId="silkscreen"/></layers></pcbView></views>
<connectors></connectors></module>'''
    return {"fzp": fzp, "pcb": pcb, "icon": icon}


# --------------------------------------------------------------------------
# Router (SELV only).  Pads: THT on both layers, SMD on top only.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class GridPoint:
    x: int
    y: int


@dataclass(frozen=True)
class RouteState:
    point: GridPoint
    layer: str


@dataclass
class Segment:
    net: str
    layer: str
    start: tuple[float, float]
    end: tuple[float, float]
    width_mm: float = TRACE_MILS * 0.0254
    start_terminal: tuple[str, int] | None = None
    end_terminal: tuple[str, int] | None = None


@dataclass(frozen=True)
class Via:
    net: str
    point: tuple[float, float]


def grid_xy(point: tuple[float, float]) -> GridPoint:
    return GridPoint(round((point[0] - BOARD_X) / GRID), round((point[1] - BOARD_Y) / GRID))


def real_xy(point: GridPoint) -> tuple[float, float]:
    return BOARD_X + point.x * GRID, BOARD_Y + point.y * GRID


def point_to_segment(point, start, end) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    norm = dx * dx + dy * dy
    if norm == 0:
        return math.dist(point, start)
    fraction = max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / norm))
    return math.dist(point, (start[0] + fraction * dx, start[1] + fraction * dy))


def segment_rect_distance(a, b, rect) -> float:
    """Distance from segment a-b to an axis-aligned rectangle (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = rect
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    inside = True
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                inside = False
                break
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                inside = False
                break
    if inside:
        return 0.0

    def point_rect(pt):
        return math.hypot(max(x0 - pt[0], 0, pt[0] - x1), max(y0 - pt[1], 0, pt[1] - y1))

    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    return min(point_rect(a), point_rect(b), *(point_to_segment(c, a, b) for c in corners))


class PadShape:
    """Copper of one pad in scene px: circle (THT) or rectangle (SMD)."""

    def __init__(self, terminal):
        part = PART_BY_REF[terminal[0]]
        pad = part.fp.pads[terminal[1]]
        cx, cy = px(part.x + pad.x, part.y + pad.y)
        self.center = (cx, cy)
        self.layers = pad_layers(pad)
        if pad.smd:
            self.rect = (cx - pad.w / 2 * S, cy - pad.h / 2 * S, cx + pad.w / 2 * S, cy + pad.h / 2 * S)
            self.radius = None
        else:
            self.rect = None
            self.radius = pad.dia / 2 * S

    def distance(self, a, b) -> float:
        """Copper-to-centreline distance from segment a-b (a point when a == b)."""
        if self.rect is None:
            return point_to_segment(self.center, a, b) - self.radius
        return segment_rect_distance(a, b, self.rect)


def segment_distance(a, c, d, e) -> float:
    """Centreline distance between segments a-c and d-e."""
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    if (cross(a, c, d) * cross(a, c, e) < 0) and (cross(d, e, a) * cross(d, e, c) < 0):
        return 0.0
    return min(point_to_segment(a, d, e), point_to_segment(c, d, e),
               point_to_segment(d, a, c), point_to_segment(e, a, c))


class SegmentIndex:
    """Coarse spatial hash of placed tracks, for via and lead clearance checks."""

    BUCKET = 4.0 * S

    def __init__(self):
        self.buckets: dict[tuple[int, int], list[Segment]] = defaultdict(list)

    def add(self, seg: "Segment") -> None:
        x0, x1 = sorted((seg.start[0], seg.end[0]))
        y0, y1 = sorted((seg.start[1], seg.end[1]))
        for bx in range(int(x0 // self.BUCKET), int(x1 // self.BUCKET) + 1):
            for by in range(int(y0 // self.BUCKET), int(y1 // self.BUCKET) + 1):
                self.buckets[(bx, by)].append(seg)

    def near(self, a, c):
        x0, x1 = sorted((a[0], c[0]))
        y0, y1 = sorted((a[1], c[1]))
        seen = set()
        for bx in range(int((x0 - self.BUCKET) // self.BUCKET), int((x1 + self.BUCKET) // self.BUCKET) + 1):
            for by in range(int((y0 - self.BUCKET) // self.BUCKET), int((y1 + self.BUCKET) // self.BUCKET) + 1):
                for seg in self.buckets.get((bx, by), ()):
                    if id(seg) not in seen:
                        seen.add(id(seg))
                        yield seg


def collapse(points):
    if len(points) <= 2:
        return points
    result = [points[0]]
    for index in range(1, len(points) - 1):
        ax, ay = result[-1]
        bx, by = points[index]
        cx, cy = points[index + 1]
        if (math.isclose(ax, bx) and math.isclose(bx, cx)) or (math.isclose(ay, by) and math.isclose(by, cy)):
            continue
        result.append((bx, by))
    result.append(points[-1])
    return result


def pad_layers(pad: Pad) -> tuple[str, ...]:
    if pad.smd:
        return ("bottom",) if pad.bottom else ("top",)
    return ("top", "bottom")


def terminal_layers(terminal: tuple[str, int]) -> tuple[str, ...]:
    return pad_layers(PART_BY_REF[terminal[0]].fp.pads[terminal[1]])


def terminal_nets() -> dict[tuple[str, int], str]:
    """Every connected pad -> its net (routed, hand-drawn SELV fan-out and 230 V)."""
    result = {}
    for table in (NETS, MANUAL_NETS_TERMINALS, MAINS_NETS_TERMINALS):
        for net, terminals in table.items():
            for terminal in terminals:
                result[terminal] = net
    return result


def pad_radius_px(terminal: tuple[str, int]) -> float:
    pad = PART_BY_REF[terminal[0]].fp.pads[terminal[1]]
    if pad.smd:
        return math.hypot(pad.w, pad.h) / 2 * S
    return pad.dia / 2 * S


def all_pad_points() -> dict[tuple[str, int], tuple[float, float]]:
    points = {}
    for part in PARTS:
        for index in range(len(part.fp.pads)):
            points[(part.ref, index)] = px(*pad_mm(part.ref, index))
    return points


class RouteFailure(RuntimeError):
    def __init__(self, net, message):
        super().__init__(message)
        self.net = net


def route_selv(points, attempts: int = 60) -> tuple[list[Segment], list[Via]]:
    """Route all SELV nets; on failure move the failing net to the front and retry."""
    # Short local nets first (driver bases and coils, display UART), supplies last.
    priority = {"5V": 10, "GND": 5, "3V3": 20, "5V_IN": 15, "DWIN_TX": 250, "DWIN_RX": 250}
    priority.update({n: 320 if n.startswith("BASE_") else 300 for n in NETS if n.startswith(("BASE_", "COIL_"))})
    order = sorted(NETS, key=lambda n: (priority.get(n, 100), len(NETS[n])), reverse=True)
    for _ in range(attempts):
        try:
            return route_selv_once(points, order)
        except RouteFailure as failure:
            order.remove(failure.net)
            order.insert(0, failure.net)
            last = failure
    raise RuntimeError(f"Routing failed after {attempts} orderings: {last}")


def route_selv_once(points, order) -> tuple[list[Segment], list[Via]]:
    max_cell_x = int(BOARD_W / GRID) - 2
    max_cell_y = int(BOARD_H / GRID) - 2
    track_radius = TRACE_MILS * DPI / 2000
    clearance = 0.24 * S
    via_radius = 0.70 * S
    terminal_net = terminal_nets()
    # SELV area: cells at least 8 mm (+ track or via radius) from any 230 V copper.
    mains_shapes = [PadShape(t) for t, n in terminal_net.items() if n in MAINS_NETS]
    mains_shapes += [PadShape((part.ref, i)) for part in PARTS if part.ref.startswith("RL")
                     for i, pad in enumerate(part.fp.pads) if pad.name.startswith("NC")]
    mains_tracks = mains_segments()
    track_ok, via_ok = set(), set()
    for gx in range(2, max_cell_x + 1):
        for gy in range(2, max_cell_y + 1):
            c = real_xy(GridPoint(gx, gy))
            d = min([sh.distance(c, c) for sh in mains_shapes] +
                    [point_to_segment(c, t.start, t.end) - t.width_mm * S / 2 for t in mains_tracks])
            if d >= MAINS_SELV_MM * S + track_radius + 0.05 * S:
                track_ok.add(GridPoint(gx, gy))
            if d >= MAINS_SELV_MM * S + via_radius + 0.05 * S:
                via_ok.add(GridPoint(gx, gy))
    pad_data = [(t, p, PadShape(t), terminal_layers(t), terminal_net.get(t)) for t, p in points.items()]
    mounts = []
    for x, y in MOUNT_CENTERS_MM:
        shape = PadShape.__new__(PadShape)
        shape.center, shape.radius, shape.rect, shape.layers = px(x, y), MOUNT_KEEPOUT_MM * S, None, ("top", "bottom")
        mounts.append(shape)
    pad_cells: dict[str, dict[GridPoint, tuple[str, int]]] = {"top": {}, "bottom": {}}
    for t, p, _, layers, _ in pad_data:
        for layer in layers:
            pad_cells[layer][grid_xy(p)] = t
    occupied = {"top": set(), "bottom": set()}
    segments: list[Segment] = []
    vias: list[Via] = []
    placed = {"top": SegmentIndex(), "bottom": SegmentIndex()}
    leads = {"top": SegmentIndex(), "bottom": SegmentIndex()}

    def emit(seg: Segment, is_lead: bool = False) -> None:
        segments.append(seg)
        placed[seg.layer].add(seg)
        if is_lead:
            leads[seg.layer].add(seg)

    for net, (_, runs) in fpc_fanout().items():
        for layer, width, pts in runs:
            pts_px = [px(*q) for q in pts]
            for a, b in zip(pts_px, pts_px[1:]):
                emit(Segment(net, layer, a, b, width_mm=width), True)

    def lead(net, layer, terminal, cell):
        pad = points[terminal]
        grid = real_xy(cell)
        if pad == grid:
            return
        path = collapse([pad, (pad[0], grid[1]), grid])
        for index, (a, b) in enumerate(zip(path, path[1:])):
            emit(Segment(net, layer, a, b, start_terminal=terminal if index == 0 else None), True)

    def astar(start_terminal, tree, foreign, foreign_vias):
        start = grid_xy(points[start_terminal])
        starts = [RouteState(start, layer) for layer in terminal_layers(start_terminal)]
        queue = []
        previous = {}
        cost = {}
        serial = 0
        for state in starts:
            cost[state] = 0.0
            heapq.heappush(queue, (0.0, serial, state))
            serial += 1
        targets = tree
        while queue:
            _, _, current = heapq.heappop(queue)
            if current in targets:
                path = [current]
                while current not in starts:
                    current = previous[current]
                    path.append(current)
                return list(reversed(path))
            options = [(RouteState(GridPoint(current.point.x + dx, current.point.y + dy), current.layer), 1.0)
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            options.append((RouteState(current.point, "bottom" if current.layer == "top" else "top"), 8.0))
            for nxt, step in options:
                p = nxt.point
                if p not in track_ok and p != start:
                    continue
                owner = pad_cells[nxt.layer].get(p)
                if owner is not None and nxt not in tree and p != start:
                    continue
                if p in occupied[nxt.layer] and nxt not in tree:
                    continue
                pos, prev = real_xy(p), real_xy(current.point)
                if nxt.layer == current.layer:
                    if any(nxt.layer in shape.layers and shape.distance(prev, pos) < track_radius + clearance
                           for shape in foreign):
                        continue
                    if any(point_to_segment(v, prev, pos) < via_radius + track_radius + clearance for v in foreign_vias):
                        continue
                    if any(seg.net != current_net and segment_distance(prev, pos, seg.start, seg.end)
                           < 2 * track_radius + clearance for seg in leads[nxt.layer].near(prev, pos)):
                        continue
                else:
                    if p not in via_ok:
                        continue
                    if any(shape.distance(pos, pos) < via_radius + clearance for shape in foreign):
                        continue
                    if any(seg.net != current_net and point_to_segment(pos, seg.start, seg.end)
                           < via_radius + track_radius + clearance
                           for layer in ("top", "bottom") for seg in placed[layer].near(pos, pos)):
                        continue
                    if any(math.dist(pos, v) < 2 * via_radius + clearance for v in foreign_vias):
                        continue
                    if any(GridPoint(p.x + dx, p.y + dy) in layer_cells and nxt not in tree
                           for layer_cells in foreign_cells.values() for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                        continue
                new_cost = cost[current] + step
                if new_cost >= cost.get(nxt, 1e18):
                    continue
                cost[nxt] = new_cost
                previous[nxt] = current
                h = min(abs(p.x - g.point.x) + abs(p.y - g.point.y) for g in targets)
                serial += 1
                heapq.heappush(queue, (new_cost + h, serial, nxt))
        raise RuntimeError(f"No route from {start_terminal}")

    for net in order:
        current_net = net
        terminals = NETS[net]
        foreign = [shape for t, p, shape, layers, n in pad_data if n != net] + mounts
        foreign_vias = [v.point for v in vias if v.net != net]
        foreign_cells = {layer: occupied[layer] for layer in occupied}
        first = terminals[0]
        first_cell = grid_xy(points[first])
        tree = {RouteState(first_cell, layer) for layer in terminal_layers(first)}
        net_cells = {"top": set(), "bottom": set()}
        for state in tree:
            net_cells[state.layer].add(state.point)
        for layer in terminal_layers(first):
            lead(net, layer, first, first_cell)
        for terminal in terminals[1:]:
            start_cell = grid_xy(points[terminal])
            try:
                path = astar(terminal, tree, foreign, foreign_vias)
            except RuntimeError as exc:
                raise RouteFailure(net, f"Cannot route {net} terminal {terminal}: {exc}") from exc
            for layer in terminal_layers(terminal):
                lead(net, layer, terminal, start_cell)
            run_layer = path[0].layer
            run = [real_xy(path[0].point)]
            for before, after in zip(path, path[1:]):
                if before.layer != after.layer:
                    run = collapse(run)
                    for a, b in zip(run, run[1:]):
                        emit(Segment(net, run_layer, a, b))
                    vias.append(Via(net, real_xy(before.point)))
                    run_layer = after.layer
                    run = [real_xy(before.point)]
                else:
                    run.append(real_xy(after.point))
            run = collapse(run)
            for a, b in zip(run, run[1:]):
                emit(Segment(net, run_layer, a, b))
            for state in path:
                tree.add(state)
                net_cells[state.layer].add(state.point)
            for layer in terminal_layers(terminal):
                tree.add(RouteState(start_cell, layer))
                net_cells[layer].add(start_cell)
            # A via joins both layers at its location.
            for v in vias:
                if v.net == net:
                    cell = grid_xy(v.point)
                    tree.add(RouteState(cell, "top"))
                    tree.add(RouteState(cell, "bottom"))
        occupied["top"].update(net_cells["top"])
        occupied["bottom"].update(net_cells["bottom"])
    return segments, vias


def mains_segments() -> list[Segment]:
    result = []
    for net, runs in mains_paths().items():
        for layer, pts in runs:
            pts_px = [px(*p) for p in pts]
            for a, b in zip(pts_px, pts_px[1:]):
                if math.dist(a, b) > 1e-6:
                    result.append(Segment(net, layer, a, b, width_mm=MAINS_WIDTH.get(net, MAINS_TRACE_MM)))
    return result


def finish_segments(segments: list[Segment], vias: list[Via], points) -> list[Segment]:
    """Split tracks at T-junctions and attach pad terminals to track ends."""
    junctions: dict[tuple[str, str], set[tuple[float, float]]] = defaultdict(set)
    for s in segments:
        junctions[(s.net, s.layer)].add((round(s.start[0], 4), round(s.start[1], 4)))
        junctions[(s.net, s.layer)].add((round(s.end[0], 4), round(s.end[1], 4)))
    for v in vias:
        for layer in ("top", "bottom"):
            junctions[(v.net, layer)].add((round(v.point[0], 4), round(v.point[1], 4)))
    terminal_net = terminal_nets()
    for t, n in terminal_net.items():
        p = points[t]
        for layer in terminal_layers(t):
            junctions[(n, layer)].add((round(p[0], 4), round(p[1], 4)))
    split = []
    for s in segments:
        (ax, ay), (bx, by) = s.start, s.end
        length_sq = (bx - ax) ** 2 + (by - ay) ** 2
        if length_sq < 1e-10:
            continue
        cuts = []
        for jx, jy in junctions[(s.net, s.layer)]:
            fraction = ((jx - ax) * (bx - ax) + (jy - ay) * (by - ay)) / length_sq
            if 1e-7 < fraction < 1 - 1e-7 and point_to_segment((jx, jy), s.start, s.end) < 1e-3:
                cuts.append((fraction, (jx, jy)))
        chain = [s.start] + [p for _, p in sorted(cuts)] + [s.end]
        for a, b in zip(chain, chain[1:]):
            split.append(Segment(s.net, s.layer, a, b, s.width_mm))
    terminal_at = defaultdict(list)
    for t, n in terminal_net.items():
        p = points[t]
        terminal_at[(n, round(p[0], 4), round(p[1], 4))].append(t)
    for s in split:
        s.start_terminal = (terminal_at.get((s.net, round(s.start[0], 4), round(s.start[1], 4))) or [None])[0]
        s.end_terminal = (terminal_at.get((s.net, round(s.end[0], 4), round(s.end[1], 4))) or [None])[0]
        for t in (s.start_terminal, s.end_terminal):
            if t is not None and s.layer not in terminal_layers(t):
                raise RuntimeError(f"{s.net}: {s.layer} track ends on SMD pad {t}")
    return split


def route_everything():
    points = all_pad_points()
    selv, vias = route_selv(points)
    vias = list(dict.fromkeys(vias))
    segments = finish_segments(selv + mains_segments(), vias, points)
    return points, segments, vias


# --------------------------------------------------------------------------
# Fritzing .fz writer
# --------------------------------------------------------------------------

def connectors_node(parent, count, layer):
    node = ET.SubElement(parent, "connectors")
    for n in range(count):
        c = ET.SubElement(node, "connector", connectorId=f"connector{n}", layer=layer)
        ET.SubElement(c, "geometry", x="0", y="0")
        ET.SubElement(c, "connects")
    return node


def connect(view, connector_id, target_index, target_connector, target_layer):
    connector = view.find(f"./connectors/connector[@connectorId='{connector_id}']")
    ET.SubElement(connector.find("connects"), "connect", connectorId=target_connector,
                  modelIndex=target_index, layer=target_layer)


SCH_UNIT = 9.0   # px per 0.1 in in the schematic scene


def part_instance(part: Part, index: str, z: float) -> ET.Element:
    fp = part.fp
    x0, y0, _, _ = fp.bbox()
    instance = ET.Element("instance", moduleIdRef=module_id(fp), modelIndex=index,
                          path=f"/home/ignacia/thermostat/{fp.key}.fzp")
    ET.SubElement(instance, "property", name="value", value=part.value)
    ET.SubElement(instance, "title").text = part.ref
    views = ET.SubElement(instance, "views")
    gx, gy = px(part.x + x0, part.y + y0)
    sx, sy = part.sch[0] * SCH_UNIT, part.sch[1] * SCH_UNIT
    for view_name, layer, (x, y), dz, visible in (("breadboardView", "breadboard", (gx, gy), 0.0, "false"),
                                                  ("pcbView", "copper0" if fp.bottom else "copper1", (gx, gy), 0.1, "false"),
                                                  ("schematicView", "schematic", (sx, sy), 0.2, "true")):
        view = ET.SubElement(views, view_name, layer=layer, **({"bottom": "true"} if fp.bottom and view_name == "pcbView" else {}))
        ET.SubElement(view, "geometry", z=f"{z + dz:.4f}", x=f"{x:.4f}", y=f"{y:.4f}")
        title = ET.SubElement(view, "titleGeometry", visible=visible, x=f"{x:.4f}", y=f"{y - 9:.4f}",
                              z=f"{z + dz + 0.01:.4f}", xOffset="0", yOffset="-9", textColor="#000000", fontSize="5")
        ET.SubElement(title, "displayKey", key="")
        connectors_node(view, len(fp.pads), layer)
    return instance


def simple_instance(module, path, index, title, x_px, y_px, z=9.5, layer="copper1"):
    instance = ET.Element("instance", moduleIdRef=module, modelIndex=index, path=path)
    ET.SubElement(instance, "title").text = title
    view = ET.SubElement(ET.SubElement(instance, "views"), "pcbView", layer=layer)
    ET.SubElement(view, "geometry", z=str(z), x=f"{x_px:.4f}", y=f"{y_px:.4f}")
    return instance


def trace_instance(index, seg: Segment, z):
    instance = ET.Element("instance", moduleIdRef="WireModuleID", modelIndex=index, path=":/resources/parts/core/wire.fzp")
    ET.SubElement(instance, "title").text = f"{seg.net}_{index}"
    views = ET.SubElement(instance, "views")
    (x1, y1), (x2, y2) = seg.start, seg.end
    layer = "copper1trace" if seg.layer == "top" else "copper0trace"
    attrs = {"layer": layer}
    if seg.layer == "bottom":
        attrs["bottom"] = "true"
    view = ET.SubElement(views, "pcbView", **attrs)
    ET.SubElement(view, "geometry", z=f"{z:.4f}", x=f"{x1:.4f}", y=f"{y1:.4f}", x1="0", y1="0",
                  x2=f"{x2 - x1:.4f}", y2=f"{y2 - y1:.4f}", wireFlags="4")
    ET.SubElement(view, "wireExtras", mils=f"{seg.width_mm / 0.0254:.4f}",
                  color="#f28a00" if seg.layer == "top" else "#2f7ed8", opacity="1", banded="0")
    connectors_node(view, 2, layer)
    return instance


def schematic_wire(index, start, end, z):
    instance = ET.Element("instance", moduleIdRef="WireModuleID", modelIndex=index, path=":/resources/parts/core/wire.fzp")
    ET.SubElement(instance, "title").text = f"SCH_{index}"
    view = ET.SubElement(ET.SubElement(instance, "views"), "schematicView", layer="schematicTrace")
    (x1, y1), (x2, y2) = start, end
    ET.SubElement(view, "geometry", z=f"{z:.4f}", x=f"{x1:.4f}", y=f"{y1:.4f}", x1="0", y1="0",
                  x2=f"{x2 - x1:.4f}", y2=f"{y2 - y1:.4f}", wireFlags="128")
    ET.SubElement(view, "wireExtras", mils="9.7222", color="#404040", opacity="1", banded="0")
    connectors_node(view, 2, "schematicTrace")
    return instance


def net_label(index, label, x, y, direction, z):
    instance = ET.Element("instance", moduleIdRef="NetLabelModuleID" if direction == "right" else "LeftNetLabelModuleID",
                          modelIndex=index,
                          path=":/resources/parts/core/netlabel.fzp" if direction == "right" else ":/resources/parts/core/netlabel_left.fzp")
    ET.SubElement(instance, "property", name="label", value=label)
    ET.SubElement(instance, "title").text = label
    views = ET.SubElement(instance, "views")
    view = ET.SubElement(views, "schematicView", layer="schematic")
    ET.SubElement(view, "geometry", z=f"{z:.4f}", x=f"{x:.4f}", y=f"{y:.4f}")
    connectors_node(view, 1, "schematic")
    return instance


SCH_NET_NAMES = {"5V_IN": "+5V_IN", "5V": "+5V", "3V3": "+3V3"}


def build_xml(points, segments, vias) -> bytes:
    root = ET.Element("module", fritzingVersion="1.0.1", icon=".png")
    boards = ET.SubElement(root, "boards")
    ET.SubElement(boards, "board", moduleId="TwoLayerRectanglePCBModuleID", title="Rectangular PCB - Resizable",
                  instance="PCB1", width=f"{BOARD_W_MM}mm", height=f"{BOARD_H_MM}mm")
    views = ET.SubElement(root, "views")
    ET.SubElement(views, "view", name="breadboardView", backgroundColor="#ffffff", gridSize="0.1in", showGrid="1",
                  alignToGrid="1", viewFromBelow="0")
    ET.SubElement(views, "view", name="schematicView", backgroundColor="#ffffff", gridSize="0.1in", showGrid="1",
                  alignToGrid="1", viewFromBelow="0")
    ET.SubElement(views, "view", name="pcbView", backgroundColor="#333333", gridSize="0.05in", showGrid="1",
                  alignToGrid="1", viewFromBelow="0", GPG_Keepout="", autorouteViaHoleSize="", DRC_Keepout="",
                  autorouteViaRingThickness="", autorouteTraceWidth=str(int(TRACE_MILS)))
    instances = ET.SubElement(root, "instances")
    board = ET.SubElement(instances, "instance", moduleIdRef="TwoLayerRectanglePCBModuleID", modelIndex="1",
                          path=":/resources/parts/core/rectangle_pcb_two_layers.fzp")
    ET.SubElement(board, "property", name="layers", value="2")
    ET.SubElement(board, "property", name="width", value=str(BOARD_W_MM))
    ET.SubElement(board, "property", name="height", value=str(BOARD_H_MM))
    ET.SubElement(board, "title").text = "THERMOSTAT REV B 84x84"
    board_views = ET.SubElement(board, "views")
    ET.SubElement(ET.SubElement(board_views, "pcbView", layer="board"), "geometry", z="1.5", x=str(BOARD_X), y=str(BOARD_Y))

    part_index, part_inst = {}, {}
    for number, part in enumerate(PARTS, start=100):
        index = str(number)
        part_index[part.ref] = index
        inst = part_instance(part, index, 2.0 + number / 1000)
        instances.append(inst)
        part_inst[part.ref] = inst
    for number, (x, y) in enumerate(MOUNT_CENTERS_MM, start=1):
        cx, cy = px(x, y)
        instances.append(simple_instance("ThermostatRevBMount", "/home/ignacia/thermostat/rb_mount.fzp",
                                         str(9000 + number), f"H{number}", cx - 3.5 * S, cy - 3.5 * S))
    instances.append(simple_instance("ThermostatRevBSilk", "/home/ignacia/thermostat/rb_silk.fzp", "9100", "LEGEND",
                                     BOARD_X, BOARD_Y, z=9.6, layer="silkscreen"))

    # PCB traces and vias.
    wires = {}
    ends = defaultdict(list)
    term_ends = defaultdict(list)
    for number, seg in enumerate(segments, start=1000):
        index = str(number)
        wire = trace_instance(index, seg, 5.0 + number / 100000)
        instances.append(wire)
        wires[index] = wire
        for key, terminal, cid in ((seg.start, seg.start_terminal, "connector0"), (seg.end, seg.end_terminal, "connector1")):
            ends[(seg.net, seg.layer, round(key[0], 4), round(key[1], 4))].append((index, cid))
            if terminal:
                term_ends[terminal].append((index, cid))
    for group in ends.values():
        for index, cid in group:
            view = wires[index].find("./views/pcbView")
            for other, ocid in group:
                if (other, ocid) != (index, cid):
                    connect(view, cid, other, ocid, view.attrib["layer"])
    for terminal, group in term_ends.items():
        ref, pad = terminal
        part_view = part_inst[ref].find("./views/pcbView")
        for index, cid in group:
            wire_view = wires[index].find("./views/pcbView")
            connect(part_view, f"connector{pad}", index, cid, wire_view.attrib["layer"])
            connect(wire_view, cid, part_index[ref], f"connector{pad}",
                    "copper0" if PART_BY_REF[ref].fp.bottom else "copper1")
    for number, via in enumerate(vias, start=8000):
        index = str(number)
        vx, vy = via.point
        inst = simple_instance("ThermostatRevBVia", "/home/ignacia/thermostat/rb_via.fzp", index, f"VIA_{via.net}",
                               vx - 0.7 * S, vy - 0.7 * S, z=8.0 + number / 100000, layer="copper0")
        via_view = inst.find("./views/pcbView")
        connectors_node(via_view, 1, "copper0")
        for layer in ("top", "bottom"):
            for windex, cid in ends.get((via.net, layer, round(vx, 4), round(vy, 4)), []):
                wview = wires[windex].find("./views/pcbView")
                connect(via_view, "connector0", windex, cid, wview.attrib["layer"])
                connect(wview, cid, index, "connector0", "copper0")
        instances.append(inst)

    # Schematic: a stub wire and a net label on every connected pin.
    net_of = terminal_nets()
    number = 20000
    for part in PARTS:
        sym = part.fp.symbol
        for pad, x, y, side, _ in sym.pins:
            net = net_of.get((part.ref, pad))
            if net is None or side == "hidden":
                continue
            px0 = (part.sch[0] + x) * SCH_UNIT
            py0 = (part.sch[1] + y) * SCH_UNIT
            dx, dy = {"left": (-2, 0), "right": (2, 0), "top": (0, -2), "bottom": (0, 2)}[side]
            px1, py1 = px0 + dx * SCH_UNIT, py0 + dy * SCH_UNIT
            wire_index, label_index = str(number), str(number + 1)
            number += 2
            wire = schematic_wire(wire_index, (px0, py0), (px1, py1), 6.0 + number / 100000)
            label_name = SCH_NET_NAMES.get(net, net)
            direction = "left" if side == "left" else "right"
            lx = px1 - (len(label_name) * 4.6 + 6) if direction == "left" else px1
            label = net_label(label_index, label_name, lx, py1 - 4.5, direction, 7.0 + number / 100000)
            wview = wire.find("./views/schematicView")
            pview = part_inst[part.ref].find("./views/schematicView")
            lview = label.find("./views/schematicView")
            connect(wview, "connector0", part_index[part.ref], f"connector{pad}", "schematic")
            connect(pview, f"connector{pad}", wire_index, "connector0", "schematicTrace")
            connect(wview, "connector1", label_index, "connector0", "schematic")
            connect(lview, "connector0", wire_index, "connector1", "schematicTrace")
            instances.append(wire)
            instances.append(label)
    ET.indent(root, space=" ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def unique_footprints() -> list[Footprint]:
    seen = {}
    for part in PARTS:
        seen.setdefault(part.fp.key, part.fp)
    return list(seen.values())


def write_fzz(output: Path, xml: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{output.name}.", dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f"{SKETCH}.fz", xml)
            archive.writestr("part.rb_via.fzp", VIA_FZP)
            archive.writestr("svg.pcb.rb_via_pcb.svg", VIA_PCB_SVG)
            archive.writestr("svg.icon.rb_via_icon.svg", VIA_ICON_SVG)
            archive.writestr("part.rb_mount.fzp", MOUNT_FZP)
            archive.writestr("svg.pcb.rb_mount_pcb.svg", MOUNT_PCB_SVG)
            archive.writestr("svg.icon.rb_mount_icon.svg", MOUNT_ICON_SVG)
            silk = board_silk_assets()
            archive.writestr("part.rb_silk.fzp", silk["fzp"])
            archive.writestr("svg.pcb.rb_silk_pcb.svg", silk["pcb"])
            archive.writestr("svg.icon.rb_silk_icon.svg", silk["icon"])
            for fp in unique_footprints():
                assets = footprint_assets(fp)
                archive.writestr(f"part.{fp.key}.fzp", assets["fzp"])
                for view in ("pcb", "breadboard", "icon", "schematic"):
                    archive.writestr(f"svg.{view}.{fp.key}_{view}.svg", assets[view])
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / f"{SKETCH}.fzz")
    args = parser.parse_args()
    points, segments, vias = route_everything()
    write_fzz(args.output, build_xml(points, segments, vias))
    print(f"Built {args.output}: {BOARD_W_MM:.0f}x{BOARD_H_MM:.0f} mm, {len(PARTS)} parts, "
          f"{len(NETS)} SELV + {len(MAINS_NETS_TERMINALS)} mains nets, {len(segments)} tracks, {len(vias)} vias")


if __name__ == "__main__":
    main()
