#!/usr/bin/env python3
"""Build the 84 x 84 mm Rev B thermostat board (Fritzing project).

Rev B carries the three Hongfa HF115F/005-1ZS3 relays and the 230 V terminal
on the PCB.  The 230 V copper lives in the upper band of the board; every
SELV conductor is kept at least 8 mm away (reinforced insulation), checked by
validate_rev_b.py.  The NodeMCU plugs into sockets (dual footprint: 0.9" and
1.1" row spacing), passives and transistors are SMD on the top side, and
5 V comes from an external isolated charger.

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
SELV_MIN_Y_MM = 37.6                # SELV track centres stay below this line
MAINS_SELV_MM = 8.0                 # reinforced clearance (validator)
MAINS_MAINS_MM = 2.4                # functional clearance between 230 V nets
# (4, 46) instead of (4, 80): the NodeMCU module (LoLin v3, 58 x 31 mm) covers the
# bottom-left corner, so a standoff cannot reach the board there.
MOUNT_CENTERS_MM = ((4.0, 4.0), (80.0, 4.0), (4.0, 46.0), (80.0, 80.0))
NODE_MODULE_MM = (2.0, 50.0, 60.0, 81.0)   # LoLin v3 outline over the sockets (x0, y0, x1, y1)
MOUNT_DRILL_MM = 3.2
MOUNT_KEEPOUT_MM = 3.5
SKETCH = "thermostat_rev_b"
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
NODE_OUTER, NODE_INNER = 13.97, 11.43


def node_pad(row: str, k: int, outer: bool) -> int:
    """Pad index in the NodeMCU footprint: T/B row, pin k (0 = USB end)."""
    return (0 if row == "T" else 30) + k * 2 + (0 if outer else 1)


def fp_nodemcu() -> Footprint:
    pads = []
    for row, names, sign in (("T", NODE_TOP, -1), ("B", NODE_BOTTOM, 1)):
        for k, name in enumerate(names):
            x = (k - 7) * 2.54
            pads.append(Pad(f"{row}{k:02d} {name}", x, sign * NODE_OUTER, drill=1.0, dia=1.7))
            pads.append(Pad(f"{row}{k:02d} {name}'", x, sign * NODE_INNER, drill=1.0, dia=1.7, sch_hidden=True))
    strip = 19.05
    bodies = [(-strip, -15.24, strip, -10.16), (-strip, 10.16, strip, 15.24)]
    silk = [rect_lines(-strip, -15.24, strip, -10.16), rect_lines(-strip, 10.16, strip, 15.24),
            [(-strip - 1.2, -1.5), (-strip - 1.2, 1.5)]]
    left = [(node_pad("T", k, True), NODE_TOP[k]) for k in range(15)]
    right = [(node_pad("B", k, True), NODE_BOTTOM[k]) for k in range(15)]
    hidden = {node_pad(r, k, False): node_pad(r, k, True) for r in "TB" for k in range(15)}
    symbol = box_symbol("NODEMCU ESP8266", left, right, width=10, hidden=hidden)
    buses = [[node_pad(r, k, True), node_pad(r, k, False)] for r in "TB" for k in range(15)]
    return Footprint("rb_nodemcu_dual", "NodeMCU socket, 0.9\" and 1.1\" rows", "U",
                     "Two 1x15 female headers; outer rows = LoLin v3 (27.94 mm), inner rows = Amica v2 (22.86 mm)",
                     pads, bodies, silk=silk, buses=buses, symbol=symbol)


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


RELAY_Y = 43.0 - RELAY_COIL_Y        # body centre, coil pins at y = 43.0
RELAY_X = (27.0, 42.0, 57.0)
NODE_X, NODE_Y = 31.78, 65.5

R_0805 = fp_0805("R", "res")
C_0805 = fp_0805("C", "cap")
DIODE = rotated(fp_sod123(), 180)     # anode on the left, next to the transistor
NPN = fp_sot23()

BOM_INFO = {
    "relay": {"mpn": "HF115F/005-1ZS3", "mfr": "Hongfa", "lcsc": "C9225", "type": "THT",
              "desc": "Relay SPDT 16 A 250 VAC, 5 V coil 62 ohm (variant ...AF with AgSnO2 also fits)"},
    "mains_terminal": {"mpn": "1715747 (MKDS 1,5/4-5,08)", "mfr": "Phoenix Contact", "lcsc": "", "type": "THT",
                       "desc": "Screw terminal 4P 5.08 mm 250 V 17.5 A (230 V side: L, COMP, CALOR, VENT)"},
    "fuse": {"mpn": "37416300000 (TR5 T6.3A)", "mfr": "Littelfuse", "lcsc": "", "type": "THT",
             "desc": "Fuse TR5 time-lag 6.3 A 250 VAC, 5.08 mm (alt. Schurter MST 250 0034.6623)"},
    "power_terminal": {"mpn": "1715721 (MKDS 1,5/2-5,08)", "mfr": "Phoenix Contact", "lcsc": "C480516", "type": "THT",
                       "desc": "Screw terminal 2P 5.08 mm, 5 V input"},
    "xh2": {"mpn": "B2B-XH-A(LF)(SN)", "mfr": "JST", "lcsc": "C158012", "type": "THT", "desc": "JST XH 2P vertical"},
    "xh3": {"mpn": "B3B-XH-A(LF)(SN)", "mfr": "JST", "lcsc": "C144394", "type": "THT", "desc": "JST XH 3P vertical"},
    "xh4": {"mpn": "B4B-XH-A(LF)(SN)", "mfr": "JST", "lcsc": "C144395", "type": "THT", "desc": "JST XH 4P vertical"},
    "socket15": {"mpn": "1x15 female header 2.54 mm, 8.5 mm", "mfr": "generic", "lcsc": "", "type": "THT",
                 "desc": "NodeMCU socket (2 pcs) in the OUTER rows for LoLin v3 / INNER rows for Amica v2"},
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


# 230 V side.
add("J20", fp_mkds(4, ["L", "COMP", "CALOR", "VENT"], True), 39.46, 6.9, "MKDS 4P 230V", "mains_terminal", (0, 0))
add("F2", fp_tr5(), 16.46, 6.9, "T6.3A 250V", "fuse", (22, 2))
for index, (name, x) in enumerate(zip(("COMP", "HEAT", "FAN"), RELAY_X), start=1):
    add(f"RL{index}", fp_relay(), x, RELAY_Y, f"HF115F 5V {name}", "relay", (44 + 28 * (index - 1), 0))

# SELV side.
add("U1", fp_nodemcu(), NODE_X, NODE_Y, "NodeMCU ESP8266", "socket15", (0, 24))
for index, (name, y) in enumerate((("COMP", 48.6), ("HEAT", 53.8), ("FAN", 59.0))):
    r_base, r_pull, q, d = 2 * index + 1, 2 * index + 2, index + 1, index + 1
    sy = 24 + index * 10
    add(f"R{r_base}", R_0805, 53.0, y - 1.1, "1k", "r1k", (36, sy))
    add(f"R{r_pull}", R_0805, 53.0, y + 1.1, "10k", "r10k", (36, sy + 4))
    add(f"Q{q}", NPN, 57.4, y, "BC817-40", "npn", (60, sy))
    add(f"D{d}", DIODE, 62.2, y, "1N4148W", "diode", (76, sy))
add("J1", fp_mkds(2, ["+5V", "GND"], False), 75.6, 52.0, "5V IN", "power_terminal", (112, 24))
add("F1", fp_1812(), 76.5, 42.5, "1.1A PTC", "ptc", (132, 24))
add("C1", fp_radial_cap(), 67.0, 43.0, "220uF 16V", "c220u", (132, 29))
add("C2", C_0805, 66.5, 48.6, "100nF", "c100n", (132, 34))
add("J2", fp_jstxh(4, ["+5V", "GND", "TX", "RX"]), 75.0, 62.0, "DWIN UART", "xh4", (112, 30))
add("J5", fp_jstxh(4, ["3V3", "GND", "SCL", "SDA"]), 75.0, 69.5, "RTC I2C", "xh4", (112, 38))
add("J3", fp_jstxh(3, ["3V3", "DATA", "GND"]), 70.5, 77.0, "DHT22", "xh3", (112, 46))
add("J4", fp_jstxh(2, ["D0", "3V3"]), 58.5, 77.0, "ON/OFF", "xh2", (112, 53))
add("C3", C_0805, 58.5, 71.0, "100nF", "c100n", (132, 39))
for ref, y, value, key, sch in (("R16", 59.0, "10k", "r10k", (36, 58)), ("R18", 61.6, "1k", "r1k", (60, 58)),
                                ("R17", 64.2, "10k", "r10k", (36, 62)), ("R19", 66.8, "1k", "r1k", (60, 62)),
                                ("R15", 69.4, "10k", "r10k", (36, 66)), ("R9", 72.0, "10k", "r10k", (60, 66))):
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
    return [("U1", node_pad(row, k, True)), ("U1", node_pad(row, k, False))]


# SELV nets (auto-routed).  Order inside each list: first terminal seeds the tree.
NETS: dict[str, list[tuple[str, int]]] = {
    "5V_IN": [T("J1", "+5V"), T("F1", "1")],
    "5V": [T("F1", "2"), T("C1", "+"), T("C2", "1"), T("D1", "K"), T("D2", "K"), T("D3", "K"),
           T("RL3", "A1"), T("RL2", "A1"), T("RL1", "A1"), *NODE("T", 0), T("J2", "+5V")],
    "GND": [T("J1", "GND"), T("C1", "-"), T("C2", "2"), T("Q1", "E"), T("Q2", "E"), T("Q3", "E"),
            T("R2", "2"), T("R4", "2"), T("R6", "2"), *NODE("B", 8), *NODE("T", 1),
            T("J2", "GND"), T("J5", "GND"), T("J3", "GND"), T("R15", "2"), T("C3", "2")],
    "3V3": [*NODE("B", 9), T("C3", "1"), T("J3", "3V3"), T("J5", "3V3"), T("J4", "3V3"),
            T("R9", "2"), T("R16", "2"), T("R17", "2")],
    "D0_ONOFF": [*NODE("B", 14), T("R15", "1"), T("J4", "D0")],
    "D1_SCL": [*NODE("B", 13), T("J5", "SCL")],
    "D2_SDA": [*NODE("B", 12), T("J5", "SDA")],
    "D3_RXD": [*NODE("B", 11), T("R16", "1"), T("R18", "1")],
    "DWIN_TX": [T("R18", "2"), T("J2", "TX")],
    "D4_TXD": [*NODE("B", 10), T("R17", "1"), T("R19", "1")],
    "DWIN_RX": [T("R19", "2"), T("J2", "RX")],
    "D5_DHT": [*NODE("B", 7), T("R9", "1"), T("J3", "DATA")],
    "D7_COMP": [*NODE("B", 5), T("R1", "1")],
    "D8_HEAT": [*NODE("B", 4), T("R3", "1")],
    "D6_FAN": [*NODE("B", 6), T("R5", "1")],
    "BASE_COMP": [T("R1", "2"), T("R2", "1"), T("Q1", "B")],
    "BASE_HEAT": [T("R3", "2"), T("R4", "1"), T("Q2", "B")],
    "BASE_FAN": [T("R5", "2"), T("R6", "1"), T("Q3", "B")],
    "COIL_COMP": [T("Q1", "C"), T("D1", "A"), T("RL1", "A2")],
    "COIL_HEAT": [T("Q2", "C"), T("D2", "A"), T("RL2", "A2")],
    "COIL_FAN": [T("Q3", "C"), T("D3", "A"), T("RL3", "A2")],
}

# 230 V nets: hand-drawn 2.5 mm tracks, (layer, [points mm]).
MAINS_NETS_TERMINALS: dict[str, list[tuple[str, int]]] = {
    "L_IN": [T("J20", "L"), T("F2", "2")],
    "L_FUSED": [T("F2", "1")] + [T(f"RL{i}", n) for i in (1, 2, 3) for n in ("COM", "COM'")],
    "OUT_COMP": [T("J20", "COMP"), T("RL1", "NO"), T("RL1", "NO'")],
    "OUT_HEAT": [T("J20", "CALOR"), T("RL2", "NO"), T("RL2", "NO'")],
    "OUT_FAN": [T("J20", "VENT"), T("RL3", "NO"), T("RL3", "NO'")],
}


def pad_mm(ref: str, index: int) -> tuple[float, float]:
    part = PART_BY_REF[ref]
    pad = part.fp.pads[index]
    return part.x + pad.x, part.y + pad.y


def _p(ref, name):
    return pad_mm(*T(ref, name))


def mains_paths() -> dict[str, list[tuple[str, list[tuple[float, float]]]]]:
    j_l, j_c, j_h, j_f = (_p("J20", n) for n in ("L", "COMP", "CALOR", "VENT"))
    f_1, f_2 = _p("F2", "1"), _p("F2", "2")
    com = [(_p(f"RL{i}", "COM"), _p(f"RL{i}", "COM'")) for i in (1, 2, 3)]
    no = [(_p(f"RL{i}", "NO"), _p(f"RL{i}", "NO'")) for i in (1, 2, 3)]
    jog_y = 12.4
    bus = [f_1, (f_1[0], com[0][0][1])] + [p for pair in com for p in pair]
    return {
        "L_IN": [("top", [j_l, f_2])],
        "L_FUSED": [("bottom", bus)],
        "OUT_COMP": [("top", [no[0][0], no[0][1]]),
                     ("top", [no[0][1], (no[0][1][0], jog_y), (j_c[0], jog_y), j_c])],
        "OUT_HEAT": [("top", [no[1][0], (j_h[0], no[1][0][1]), no[1][1]]),
                     ("top", [(j_h[0], no[1][0][1]), j_h])],
        "OUT_FAN": [("top", [no[2][0], no[2][1]]),
                    ("top", [no[2][0], (no[2][0][0], jog_y), (j_f[0], jog_y), j_f])],
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


def footprint_assets(fp: Footprint) -> dict[str, str]:
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
    y = 33.3
    x = 1.0
    while x < 83.0:
        lines.append([(x, y), (min(x + 1.6, 83.0), y)])
        x += 2.6
    text("! PELIGRO 230V~", 64.5, 15.0, 1.3)
    text("NO TOCAR", 66.2, 17.4, 1.3)
    text("TERMOSTATO", 66.0, 23.0, 1.3)
    text("REV B 84X84", 66.0, 25.2, 1.3)
    text("2026-10", 66.0, 27.4, 1.3)
    text("SELV 5V", 66.0, 34.5, 1.2)
    text("J20: L COMP CALOR VENT", 50.8, 3.0, 1.15)
    text("(4) (1) (3)", 64.3, 5.2, 1.15)
    text("F2 T6.3A", 16.46, 11.6, 1.1, "middle")
    for index, (name, x) in enumerate(zip(("COMP", "CALOR", "VENT"), RELAY_X), start=1):
        text(f"RL{index}", x, 36.0, 1.2, "middle")
        text(name, x, 38.2, 1.0, "middle")
        text("NC", x, RELAY_Y - 3.22 - 0.45, 0.9, "middle")
        text("COM", x, RELAY_Y - 8.26 - 0.45, 0.9, "middle")
        text("NO", x, RELAY_Y - 13.3 - 0.45, 0.9, "middle")
    # Connector legends.
    text("+5V GND", 75.6, 57.6, 1.0, "middle")
    text("J1 5V 2A", 75.6, 45.4, 1.0, "middle")
    text("J2 DWIN 5V G TX RX", 75.0, 65.6, 0.9, "middle")
    text("J5 RTC 3V3 G SCL SDA", 75.0, 73.1, 0.9, "middle")
    text("J3 DHT 3V3 D G", 70.5, 80.6, 0.9, "middle")
    text("J4 ON D0 3V3", 58.5, 80.6, 0.9, "middle")
    text("USB", 3.2, 63.8, 1.1)
    text("U1 NODEMCU", 31.8, 64.8, 1.4, "middle")
    text("VIN", 14.0, 47.6, 0.9, "middle")
    text("D0", 49.56, 81.2, 0.9, "middle")
    # Reference designators for the SMD/driver block.
    for ref in ("Q1", "Q2", "Q3", "D1", "D2", "D3", "F1", "C1", "C2", "C3",
                "R9", "R15", "R16", "R17", "R18", "R19"):
        part = PART_BY_REF[ref]
        if ref.startswith("R"):
            text(ref, part.x - 2.2, part.y - 0.45, 0.9, "end")
        elif ref.startswith(("Q", "D")):
            text(ref, part.x, part.y - 2.6, 0.8, "middle")
        elif ref == "F1":
            text(ref, part.x, part.y - 3.3, 0.9, "middle")
        elif ref == "C1":
            text("C1", part.x, part.y + 3.6, 0.9, "middle")
        else:
            text(ref, part.x, part.y + 1.1, 0.8, "middle")
    return lines, []


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
        self.layers = ("top",) if pad.smd else ("top", "bottom")
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


def terminal_layers(terminal: tuple[str, int]) -> tuple[str, ...]:
    pad = PART_BY_REF[terminal[0]].fp.pads[terminal[1]]
    return ("top",) if pad.smd else ("top", "bottom")


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
    priority = {"5V": 10, "GND": 5, "3V3": 20, "5V_IN": 15}
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
    min_cell_y = math.ceil(SELV_MIN_Y_MM * S / GRID)
    track_radius = TRACE_MILS * DPI / 2000
    clearance = 0.24 * S
    via_radius = 0.70 * S
    terminal_net = {t: n for n, ts in NETS.items() for t in ts}
    for name, ts in MAINS_NETS_TERMINALS.items():
        for t in ts:
            terminal_net[t] = name
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
                if not (2 <= p.x <= max_cell_x and min_cell_y <= p.y <= max_cell_y):
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
                    result.append(Segment(net, layer, a, b, width_mm=MAINS_TRACE_MM))
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
    terminal_net = {t: n for n, ts in {**NETS, **MAINS_NETS_TERMINALS}.items() for t in ts}
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
                                                  ("pcbView", "copper1", (gx, gy), 0.1, "false"),
                                                  ("schematicView", "schematic", (sx, sy), 0.2, "true")):
        view = ET.SubElement(views, view_name, layer=layer)
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
            connect(wire_view, cid, part_index[ref], f"connector{pad}", "copper1")
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
    net_of = {t: n for n, ts in {**NETS, **MAINS_NETS_TERMINALS}.items() for t in ts}
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
