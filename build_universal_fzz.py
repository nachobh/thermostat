#!/usr/bin/env python3
"""Build the fabrication-oriented, SELV-only thermostat Fritzing project.

All field modules are connected through polarized 2.50 mm JST XH headers.
Only the three SSR input drivers and their passive components live on the PCB.
No mains-voltage conductor or SSR output is present on this board.
"""

from __future__ import annotations

import argparse
import heapq
import math
import re
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


PART_ROOT = Path("/usr/share/fritzing/parts")
CORE = PART_ROOT / "core"
SVG_ROOT = PART_ROOT / "svg" / "core"
DPI = 90.0
GRID = 3.0  # 0.847 mm; precise escape routing around 2.5 mm-pitch pads.
BOARD_X, BOARD_Y = 100.0, 0.0
BOARD_W_MM, BOARD_H_MM = 100.0, 100.0
BOARD_W = BOARD_W_MM / 25.4 * DPI
BOARD_H = BOARD_H_MM / 25.4 * DPI
TRACE_MILS = 24.0
MOUNT_CENTERS_MM = ((5.0, 5.0), (95.0, 5.0), (5.0, 95.0), (95.0, 95.0))
MOUNT_DRILL_MM = 3.0
MOUNT_KEEPOUT_MM = 3.5  # Clearance for a roughly 6 mm screw head/washer.

MOUNT_PCB_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"
 width="7mm" height="7mm" viewBox="0 0 7 7">
 <g id="copper1"><g id="copper0">
  <circle id="nonconn0" cx="3.5" cy="3.5" r="1.5" fill="#000000"/>
 </g></g>
 <g id="silkscreen"><circle cx="3.5" cy="3.5" r="3.25" fill="none"
  stroke="#f0f0f0" stroke-width="0.2"/></g>
</svg>'''
MOUNT_FZP = '''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="ThermostatMountingHole3mm">
 <version>1</version><author>thermostat project</author>
 <title>Mounting hole NPTH 3 mm</title><label>H</label>
 <description>Unplated 3.0 mm mounting hole; 7 mm copper/component keepout.</description>
 <properties><property name="family">mounting hole</property><property name="package">NPTH 3mm</property></properties>
 <views><iconView><layers image="icon/thermostat_mount_icon.svg"><layer layerId="icon"/></layers></iconView>
 <pcbView><layers image="pcb/thermostat_mount_pcb.svg"><layer layerId="copper1"/>
  <layer layerId="copper0"/><layer layerId="silkscreen"/></layers></pcbView></views>
 <connectors></connectors>
</module>'''
MOUNT_ICON_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="7mm" height="7mm" viewBox="0 0 7 7">
 <g id="icon"><circle cx="3.5" cy="3.5" r="2.8" fill="none" stroke="#888" stroke-width="0.4"/>
 <circle cx="3.5" cy="3.5" r="1.5" fill="white"/></g></svg>'''

VIA_PCB_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"
     width="1.4mm" height="1.4mm" viewBox="0 0 1.4 1.4">
  <g id="copper1">
    <circle id="connector0pad" cx="0.7" cy="0.7" r="0.5"
            fill="none" stroke="#f7bd13" stroke-width="0.4"/>
    <g id="copper0">
      <circle id="connector0pad" cx="0.7" cy="0.7" r="0.5"
              fill="none" stroke="#f7bd13" stroke-width="0.4"/>
    </g>
  </g>
</svg>
"""
VIA_ICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1.4mm" height="1.4mm" viewBox="0 0 1.4 1.4">
  <g id="icon"><circle cx="0.7" cy="0.7" r="0.6" fill="#d9a400"/><circle cx="0.7" cy="0.7" r="0.3" fill="#fff"/></g>
</svg>
"""

VIA_FZP = """<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="ThermostatViaModuleID">
  <version>1</version><author>thermostat project</author><title>Plated via 1.4/0.6 mm</title>
  <label>V</label><description>Two-layer plated through via.</description>
  <tags><tag>via</tag><tag>pcb</tag></tags>
  <properties><property name="family">via</property><property name="package">THT</property></properties>
  <views><iconView><layers image="icon/thermostat_via_icon.svg"><layer layerId="icon"/></layers></iconView>
  <pcbView><layers image="pcb/thermostat_via_pcb.svg">
    <layer layerId="copper1"/><layer layerId="copper0"/>
  </layers></pcbView></views>
  <connectors><connector id="connector0" name="via" type="male"><description>via</description>
    <views><pcbView><p layer="copper0" svgId="connector0pad"/><p layer="copper1" svgId="connector0pad"/></pcbView></views>
  </connector></connectors>
</module>
"""


def jst_xh_assets(pins: int) -> dict[str, str]:
    """Return a bundled Fritzing part for JST BxB-XH-A (top entry)."""
    module = f"ThermostatJSTXH{pins}"
    base = f"thermostat_jstxh{pins}"
    width = 4.9 + 2.5 * (pins - 1)
    pad_x = [2.45 + 2.5 * number for number in range(pins)]
    pads = "\n".join(
        f'<circle id="connector{number}pad" cx="{x:.3f}" cy="3.400" r="0.675" '
        f'fill="none" stroke="#f7bd13" stroke-width="0.450"/>'
        for number, x in enumerate(pad_x)
    )
    # Official recommendation is 0.9 mm drill for 3+ circuits. With the SVG
    # ring equation (hole = 2*r - stroke), these pads export as 0.90 mm.
    pcb = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"
 width="{width}mm" height="5.75mm" viewBox="0 0 {width} 5.75">
 <g id="copper1">{pads}<g id="copper0">{pads}</g></g>
 <g id="silkscreen"><rect x="0.10" y="0.10" width="{width - 0.2:.3f}" height="5.55"
  fill="none" stroke="#f0f0f0" stroke-width="0.20"/>
  <path d="M0.10,1.2 L0.8,1.2 L0.8,0.1" fill="none" stroke="#f0f0f0" stroke-width="0.25"/>
 </g>
</svg>'''
    view_pins = "\n".join(
        f'<circle id="connector{number}pin" cx="{x:.3f}" cy="3.400" r="0.45" fill="#8c8c8c"/>'
        for number, x in enumerate(pad_x)
    )
    simple = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"
 width="{width}mm" height="5.75mm" viewBox="0 0 {width} 5.75">
 <g id="breadboard"><rect x="0.1" y="0.1" width="{width - 0.2:.3f}" height="5.55"
  rx="0.3" fill="#f7f4df" stroke="#555" stroke-width="0.15"/>{view_pins}</g>
 <g id="icon"><rect x="0.1" y="0.1" width="{width - 0.2:.3f}" height="5.55"
  rx="0.3" fill="#f7f4df" stroke="#555" stroke-width="0.15"/></g>
</svg>'''
    schematic_pins = "\n".join(
        f'<circle id="connector{number}pin" cx="{x:.3f}" cy="3.400" r="0.25" fill="none" stroke="#555" stroke-width="0.15"/>'
        f'<circle id="connector{number}terminal" cx="{x:.3f}" cy="3.400" r="0.05" fill="none"/>'
        for number, x in enumerate(pad_x)
    )
    schematic = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"
 width="{width}mm" height="5.75mm" viewBox="0 0 {width} 5.75">
 <g id="schematic"><rect x="0.1" y="0.1" width="{width - 0.2:.3f}" height="5.55"
  fill="#fff" stroke="#555" stroke-width="0.15"/>{schematic_pins}</g>
</svg>'''
    connectors = "\n".join(
        f'''<connector id="connector{number}" name="{number + 1}" type="male"><description>Pin {number + 1}</description><views>
 <breadboardView><p layer="breadboard" svgId="connector{number}pin"/></breadboardView>
 <schematicView><p layer="schematic" svgId="connector{number}pin" terminalId="connector{number}terminal"/></schematicView>
 <pcbView><p layer="copper0" svgId="connector{number}pad"/><p layer="copper1" svgId="connector{number}pad"/></pcbView>
 </views></connector>'''
        for number in range(pins)
    )
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="{module}"><version>1</version>
 <author>thermostat project</author><title>JST XH {pins}-pin B{pins}B-XH-A</title><label>J</label>
 <description>JST XH top-entry, 2.50 mm pitch, 0.90 mm drill.</description>
 <tags><tag>JST</tag><tag>XH</tag><tag>connector</tag></tags>
 <properties><property name="family">JST XH</property><property name="package">THT</property><property name="part number">B{pins}B-XH-A</property></properties>
 <views>
  <iconView><layers image="icon/{base}_icon.svg"><layer layerId="icon"/></layers></iconView>
  <breadboardView><layers image="breadboard/{base}_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>
  <schematicView><layers image="schematic/{base}_schematic.svg"><layer layerId="schematic"/></layers></schematicView>
  <pcbView><layers image="pcb/{base}_pcb.svg"><layer layerId="copper1"/><layer layerId="silkscreen"/><layer layerId="copper0"/></layers></pcbView>
 </views><connectors>{connectors}</connectors></module>'''
    return {"fzp": fzp, "pcb": pcb, "breadboard": simple, "icon": simple, "schematic": schematic}


JST_ASSETS = {pins: jst_xh_assets(pins) for pins in (3, 4, 5)}


def terminal_assets() -> dict[str, str]:
    """Phoenix Contact MKDS 1,5/2-5,08, order 1715721."""
    pads = '\n'.join(
        f'<circle id="connector{n}pad" cx="{x:.2f}" cy="4.90" r="0.825" '
        'fill="none" stroke="#f7bd13" stroke-width="0.35"/>'
        for n, x in enumerate((2.54, 7.62))
    )
    pcb = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"
 width="10.16mm" height="9.8mm" viewBox="0 0 10.16 9.8">
 <g id="copper1">{pads}<g id="copper0">{pads}</g></g>
 <g id="silkscreen"><rect x="0.1" y="0.1" width="9.96" height="9.6"
 fill="none" stroke="#f0f0f0" stroke-width="0.20"/>
 <path d="M0.1,1.2 L1.2,1.2 L1.2,0.1" fill="none" stroke="#f0f0f0" stroke-width="0.25"/>
 <path d="M2.0,1.8 L3.1,1.8 M2.54,1.25 L2.54,2.35 M7.05,1.8 L8.2,1.8"
 fill="none" stroke="#f0f0f0" stroke-width="0.28"/>
 </g></svg>'''
    pins = ''.join(f'<circle id="connector{n}pin" cx="{x:.2f}" cy="4.9" r="0.4" fill="#777"/>'
                   for n, x in enumerate((2.54, 7.62)))
    generic = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="10.16mm" height="9.8mm" viewBox="0 0 10.16 9.8">
 <g id="breadboard"><rect width="10.16" height="9.8" fill="#268456"/>{pins}</g>
 <g id="icon"><rect width="10.16" height="9.8" fill="#268456"/></g>
 <g id="schematic"><rect x="0.2" y="0.2" width="9.76" height="9.4" fill="#fff" stroke="#555" stroke-width="0.2"/>{pins}</g>
</svg>'''
    connectors = ''.join(
        f'''<connector id="connector{n}" name="{n+1}" type="male"><description>Pin {n+1}</description><views>
        <breadboardView><p layer="breadboard" svgId="connector{n}pin"/></breadboardView>
        <schematicView><p layer="schematic" svgId="connector{n}pin"/></schematicView>
        <pcbView><p layer="copper0" svgId="connector{n}pad"/><p layer="copper1" svgId="connector{n}pad"/></pcbView>
        </views></connector>''' for n in range(2))
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="ThermostatMKDS2"><version>1</version>
<author>thermostat project</author><title>MKDS 1,5/2-5,08 1715721</title><label>J</label>
<description>Phoenix Contact 1715721, 5.08 mm pitch, 1.30 mm drill.</description>
<properties><property name="family">MKDS</property><property name="package">THT</property></properties>
<views><iconView><layers image="icon/thermostat_mkds2_icon.svg"><layer layerId="icon"/></layers></iconView>
<breadboardView><layers image="breadboard/thermostat_mkds2_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>
<schematicView><layers image="schematic/thermostat_mkds2_schematic.svg"><layer layerId="schematic"/></layers></schematicView>
<pcbView><layers image="pcb/thermostat_mkds2_pcb.svg"><layer layerId="copper1"/><layer layerId="copper0"/><layer layerId="silkscreen"/></layers></pcbView></views>
<connectors>{connectors}</connectors></module>'''
    return {'fzp': fzp, 'pcb': pcb, 'breadboard': generic, 'icon': generic, 'schematic': generic}


TERMINAL_ASSETS = terminal_assets()


def bc547_assets() -> dict[str, str]:
    """Straight 2.54 mm C-B-E TO-92 footprint for Diotec BC547B ammo pack."""
    pins = "".join(
        f'<circle id="connector{n}pad" cx="{1.1 + 2.54*n:.2f}" cy="2.85" '
        'r="0.675" fill="none" stroke="#f7bd13" stroke-width="0.45"/>'
        for n in range(3)
    )
    pcb = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"
 width="7.28mm" height="5.2mm" viewBox="0 0 7.28 5.2">
 <g id="copper1">{pins}<g id="copper0">{pins}</g></g>
 <g id="silkscreen">
  <path d="M0.35,3.85 A3.25,3.1 0 0 1 6.93,3.85 M0.35,4.85 L6.93,4.85"
        fill="none" stroke="#f0f0f0" stroke-width="0.18"/>
  <text x="1.1" y="1.15" text-anchor="middle" font-family="sans-serif" font-size="0.75" fill="#f0f0f0">C</text>
  <text x="3.64" y="1.15" text-anchor="middle" font-family="sans-serif" font-size="0.75" fill="#f0f0f0">B</text>
  <text x="6.18" y="1.15" text-anchor="middle" font-family="sans-serif" font-size="0.75" fill="#f0f0f0">E</text>
 </g></svg>'''
    generic_pins = "".join(
        f'<circle id="connector{n}pin" cx="{1.1 + 2.54*n:.2f}" cy="2.85" r="0.38" fill="#777"/>'
        for n in range(3)
    )
    generic = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="7.28mm" height="5.2mm" viewBox="0 0 7.28 5.2">
 <g id="breadboard"><rect width="7.28" height="5.2" fill="#444"/>{generic_pins}</g>
 <g id="icon"><rect width="7.28" height="5.2" fill="#444"/>{generic_pins}</g>
 <g id="schematic"><rect x="0.2" y="0.2" width="6.88" height="4.8" fill="#fff" stroke="#555" stroke-width="0.2"/>{generic_pins}</g>
</svg>'''
    connectors = "".join(
        f'''<connector id="connector{n}" name="{name}" type="male"><description>{name}</description><views>
         <breadboardView><p layer="breadboard" svgId="connector{n}pin"/></breadboardView>
         <schematicView><p layer="schematic" svgId="connector{n}pin"/></schematicView>
         <pcbView><p layer="copper0" svgId="connector{n}pad"/><p layer="copper1" svgId="connector{n}pad"/></pcbView>
         </views></connector>''' for n, name in enumerate(("C", "B", "E"))
    )
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.1" moduleId="ThermostatBC547B"><version>1</version>
 <author>thermostat project</author><title>BC547B C-B-E straight 2.54 mm</title><label>Q</label>
 <description>Diotec BC547B TO-92 straight C-B-E, 2.54 mm pitch, flat side on marked edge.</description>
 <properties><property name="family">transistor</property><property name="package">TO-92 THT</property></properties>
 <views><iconView><layers image="icon/thermostat_bc547_icon.svg"><layer layerId="icon"/></layers></iconView>
 <breadboardView><layers image="breadboard/thermostat_bc547_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>
 <schematicView><layers image="schematic/thermostat_bc547_schematic.svg"><layer layerId="schematic"/></layers></schematicView>
 <pcbView><layers image="pcb/thermostat_bc547_pcb.svg"><layer layerId="copper1"/><layer layerId="copper0"/><layer layerId="silkscreen"/></layers></pcbView></views>
 <connectors>{connectors}</connectors></module>'''
    return {"fzp": fzp, "pcb": pcb, "breadboard": generic, "icon": generic, "schematic": generic}


BC547_ASSETS = bc547_assets()


@dataclass(frozen=True)
class PartKind:
    module: str
    path: str
    fzp: str


KINDS = {
    "jstxh3": PartKind("ThermostatJSTXH3", "/home/ignacia/thermostat/thermostat_jstxh3.fzp", "thermostat_jstxh3.fzp"),
    "jstxh4": PartKind("ThermostatJSTXH4", "/home/ignacia/thermostat/thermostat_jstxh4.fzp", "thermostat_jstxh4.fzp"),
    "jstxh5": PartKind("ThermostatJSTXH5", "/home/ignacia/thermostat/thermostat_jstxh5.fzp", "thermostat_jstxh5.fzp"),
    "terminal2": PartKind("ThermostatMKDS2", "/home/ignacia/thermostat/thermostat_mkds2.fzp", "thermostat_mkds2.fzp"),
    "bc547": PartKind("ThermostatBC547B", "/home/ignacia/thermostat/thermostat_bc547.fzp", "thermostat_bc547.fzp"),
    "resistor": PartKind("ResistorModuleID", ":/resources/parts/core/resistor.fzp", "resistor.fzp"),
    "npn": PartKind("SparkFun-DiscreteSemi-TRANSISTOR_NPN_2-PTH", ":/resources/parts/core/sparkfun-discretesemi-transistor_npn_2-pth.fzp", "sparkfun-discretesemi-transistor_npn_2-pth.fzp"),
    "ceramic": PartKind("100milCeramicCapacitorModuleID", ":/resources/parts/core/capacitor_ceramic_100mil.fzp", "capacitor_ceramic_100mil.fzp"),
    "electrolytic": PartKind("SmallElectrolyticCapacitorModuleID", ":/resources/parts/core/capacitor_electrolytic_small.fzp", "capacitor_electrolytic_small.fzp"),
    "ptc": PartKind("SparkFun-PowerIC-PTC-PTH", ":/resources/parts/core/sparkfun-poweric-ptc-pth.fzp", "sparkfun-poweric-ptc-pth.fzp"),
}


@dataclass
class Part:
    ref: str
    title: str
    kind: str
    x: float
    y: float
    connectors: int
    properties: dict[str, str] = field(default_factory=dict)


PARTS = [
    Part("J1", "J1 PWR 5V-3V3-GND", "jstxh3", 132, 12, 3),
    # Deliberate order prevents signal crossings: D6, D8, D7, D5.
    Part("J2", "J2 NODE D6-D8-D7-D5", "jstxh4", 170, 12, 4),
    Part("J3", "J3 NODE D1-D2-A0-GND", "jstxh4", 110, 70, 4),
    Part("J4", "J4 NODE D0-D3-D4-GND", "jstxh4", 290, 120, 4),
    Part("J5", "J5 OLED1 3V3-GND-SCL-SDA", "jstxh4", 235, 70, 4),
    Part("J6", "J6 OLED2 3V3-GND-SCL-SDA", "jstxh4", 305, 70, 4),
    Part("J7", "J7 RTC 3V3-GND-SCL-SDA", "jstxh4", 375, 70, 4),
    Part("J8", "J8 DHT 3V3-DATA-GND", "jstxh3", 180, 120, 3),
    Part("J9", "J9 POT 3V3-A0-GND", "jstxh3", 110, 170, 3),
    Part("J10", "J10 CTRL D0-D3-D4-GND-3V3", "jstxh5", 335, 120, 5),
    Part("F1", "F1 PTC 0.30A HOLD", "ptc", 125, 40, 2),
    Part("C7", "C7 100nF 5V", "ceramic", 115, 110, 2, {"capacitance": "100 nF"}),
    Part("C8", "C8 100uF 5V", "electrolytic", 145, 110, 2, {"capacitance": "100 uF", "voltage": "10V"}),
    Part("C9", "C9 100nF 3V3", "ceramic", 115, 145, 2, {"capacitance": "100 nF"}),
    Part("C10", "C10 47uF 3V3", "electrolytic", 145, 145, 2, {"capacitance": "47 uF", "voltage": "10V"}),
    Part("R7", "R7 4k7 SDA DNP", "resistor", 225, 145, 2, {"resistance": "4.7k"}),
    Part("R8", "R8 4k7 SCL DNP", "resistor", 285, 145, 2, {"resistance": "4.7k"}),
    Part("R9", "R9 4k7 DHT DNP", "resistor", 180, 155, 2, {"resistance": "4.7k"}),
    Part("R10", "R10 0R GND BRIDGE", "resistor", 165, 190, 2, {"resistance": "0"}),
    Part("R11", "R11 0R GND LOGIC BRIDGE", "resistor", 165, 215, 2, {"resistance": "0"}),
    Part("R12", "R12 0R GND I2C BRIDGE", "resistor", 215, 110, 2, {"resistance": "0"}),
    Part("R13", "R13 0R 3V3 I2C BRIDGE", "resistor", 230, 135, 2, {"resistance": "0"}),
    Part("R14", "R14 0R 3V3 SENSOR BRIDGE", "resistor", 125, 130, 2, {"resistance": "0"}),
    Part("R15", "R15 10k D0 PULLDOWN", "resistor", 335, 160, 2, {"resistance": "10k"}),
    Part("R16", "R16 10k D3 PULLUP", "resistor", 220, 165, 2, {"resistance": "10k"}),
    Part("R17", "R17 10k D4 PULLUP", "resistor", 290, 160, 2, {"resistance": "10k"}),
    # Compressor channel.
    Part("R1", "R1 1k COMP", "resistor", 215, 190, 2, {"resistance": "1k"}),
    Part("R2", "R2 10k COMP", "resistor", 285, 190, 2, {"resistance": "10k"}),
    Part("Q1", "Q1 BC547B COMP CBE", "bc547", 355, 190, 3),
    Part("C1", "C1 100nF COMP", "ceramic", 390, 190, 2, {"capacitance": "100 nF"}),
    Part("J11", "J11 COMP4 +5-CTRL", "terminal2", 410, 183, 2),
    # Heating channel.
    Part("R3", "R3 1k HEAT", "resistor", 215, 240, 2, {"resistance": "1k"}),
    Part("R4", "R4 10k HEAT", "resistor", 285, 240, 2, {"resistance": "10k"}),
    Part("Q2", "Q2 BC547B HEAT CBE", "bc547", 355, 240, 3),
    Part("C2", "C2 100nF HEAT", "ceramic", 390, 240, 2, {"capacitance": "100 nF"}),
    Part("J12", "J12 HEAT1 +5-CTRL", "terminal2", 410, 233, 2),
    # Fan channel.
    Part("R5", "R5 1k FAN", "resistor", 215, 290, 2, {"resistance": "1k"}),
    Part("R6", "R6 10k FAN", "resistor", 285, 290, 2, {"resistance": "10k"}),
    Part("Q3", "Q3 BC547B FAN CBE", "bc547", 355, 290, 3),
    Part("C3", "C3 100nF FAN", "ceramic", 390, 290, 2, {"capacitance": "100 nF"}),
    Part("J13", "J13 FAN3 +5-CTRL", "terminal2", 410, 283, 2),
]


def pin(ref: str, number: int) -> tuple[str, str]:
    return ref, f"connector{number}"


# Custom BC547 part: connector0=C, connector1=B, connector2=E.
NETS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "5V_RAW": ("bottom", [pin("J1", 0), pin("F1", 0)]),
    "5V_SSR": ("bottom", [pin("F1", 1), pin("C7", 0), pin("C8", 1), pin("C1", 0), pin("C2", 0), pin("C3", 0), pin("J11", 0), pin("J12", 0), pin("J13", 0)]),
    "3V3_ENTRY": ("top", [pin("J1", 1), pin("C9", 0), pin("C10", 1), pin("R13", 0), pin("R14", 0)]),
    "3V3_I2C": ("top", [pin("R13", 1), pin("J5", 0), pin("J6", 0), pin("J7", 0), pin("J10", 4), pin("R7", 1), pin("R8", 1), pin("R16", 1), pin("R17", 1)]),
    "3V3_SENSOR": ("top", [pin("R14", 1), pin("J8", 0), pin("J9", 0), pin("R9", 1)]),
    "GND_ENTRY": ("bottom", [pin("J1", 2), pin("C7", 1), pin("C8", 0), pin("C9", 1), pin("C10", 0), pin("R10", 0), pin("R11", 0)]),
    "GND_LOGIC": ("bottom", [pin("R11", 1), pin("J3", 3), pin("J4", 3), pin("J8", 2), pin("J9", 2), pin("J10", 3), pin("R12", 0), pin("R15", 1)]),
    "GND_I2C": ("bottom", [pin("R12", 1), pin("J5", 1), pin("J6", 1), pin("J7", 1)]),
    "GND_DRIVE": ("bottom", [pin("R10", 1), pin("R2", 1), pin("R4", 1), pin("R6", 1), pin("Q1", 2), pin("Q2", 2), pin("Q3", 2)]),
    "D6_FAN": ("top", [pin("J2", 0), pin("R5", 0)]),
    "D8_HEAT": ("top", [pin("J2", 1), pin("R3", 0)]),
    "D7_COMP": ("top", [pin("J2", 2), pin("R1", 0)]),
    "D5_DHT": ("bottom", [pin("J2", 3), pin("J8", 1), pin("R9", 0)]),
    "D1_SCL": ("top", [pin("J3", 0), pin("J5", 2), pin("J6", 2), pin("J7", 2), pin("R8", 0)]),
    "D2_SDA": ("bottom", [pin("J3", 1), pin("J5", 3), pin("J6", 3), pin("J7", 3), pin("R7", 0)]),
    "A0": ("top", [pin("J3", 2), pin("J9", 1)]),
    "D0_OFF": ("top", [pin("J4", 0), pin("J10", 0), pin("R15", 0)]),
    "D3_MENU": ("bottom", [pin("J4", 1), pin("J10", 1), pin("R16", 0)]),
    "D4_SELECT": ("top", [pin("J4", 2), pin("J10", 2), pin("R17", 0)]),
    "BASE_COMP": ("top", [pin("R1", 1), pin("R2", 0), pin("Q1", 1)]),
    "CTRL_COMP": ("top", [pin("Q1", 0), pin("C1", 1), pin("J11", 1)]),
    "BASE_HEAT": ("top", [pin("R3", 1), pin("R4", 0), pin("Q2", 1)]),
    "CTRL_HEAT": ("top", [pin("Q2", 0), pin("C2", 1), pin("J12", 1)]),
    "BASE_FAN": ("top", [pin("R5", 1), pin("R6", 0), pin("Q3", 1)]),
    "CTRL_FAN": ("top", [pin("Q3", 0), pin("C3", 1), pin("J13", 1)]),
}


def length_px(value: str) -> float:
    match = re.fullmatch(r"\s*([0-9.]+)\s*(in|mm|cm|mil|px)?\s*", value)
    if not match:
        raise ValueError(f"Unsupported SVG length {value!r}")
    amount = float(match.group(1))
    unit = match.group(2) or "px"
    return {"in": DPI, "mm": DPI / 25.4, "cm": DPI / 2.54, "mil": DPI / 1000, "px": 1.0}[unit] * amount


def element_center(element: ET.Element) -> tuple[float, float]:
    a = element.attrib
    if "cx" in a and "cy" in a:
        return float(a["cx"]), float(a["cy"])
    if "x" in a and "y" in a:
        return float(a["x"]) + float(a.get("width", 0)) / 2, float(a["y"]) + float(a.get("height", 0)) / 2
    if "x1" in a and "y1" in a and "x2" in a and "y2" in a:
        return (float(a["x1"]) + float(a["x2"])) / 2, (float(a["y1"]) + float(a["y2"])) / 2
    children = [element_center(child) for child in element if child.attrib.get("id")]
    if children:
        return sum(x for x, _ in children) / len(children), sum(y for _, y in children) / len(children)
    raise ValueError(f"Cannot find center for SVG element {a.get('id')}")


def svg_path(image: str) -> Path:
    path = SVG_ROOT / image
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def pad_offsets(part: Part, view: str = "pcbView") -> dict[str, tuple[float, float]]:
    if part.kind == "terminal2":
        return {
            f"connector{number}": (x * DPI / 25.4, 4.9 * DPI / 25.4)
            for number, x in enumerate((2.54, 7.62))
        }
    if part.kind == "bc547":
        return {
            f"connector{number}": ((1.1 + 2.54 * number) * DPI / 25.4, 2.85 * DPI / 25.4)
            for number in range(3)
        }
    if part.kind in {"jstxh3", "jstxh4", "jstxh5"}:
        return {
            f"connector{number}": ((2.45 + 2.5 * number) * DPI / 25.4, 3.4 * DPI / 25.4)
            for number in range(part.connectors)
        }
    kind = KINDS[part.kind]
    root = ET.parse(CORE / kind.fzp).getroot()
    layers = root.find(f"./views/{view}/layers")
    image = layers.attrib["image"]
    svg = ET.parse(svg_path(image)).getroot()
    width = length_px(svg.attrib["width"])
    height = length_px(svg.attrib["height"])
    # Older core parts sometimes omit viewBox and express their geometry directly
    # in the same user units as width/height.
    if "viewBox" in svg.attrib:
        vb = [float(value) for value in svg.attrib["viewBox"].replace(",", " ").split()]
    else:
        vb = [0.0, 0.0, width, height]
    sx, sy = width / vb[2], height / vb[3]
    by_id = {node.attrib["id"]: node for node in svg.iter() if "id" in node.attrib}
    result = {}
    for connector in root.findall("./connectors/connector"):
        connector_id = connector.attrib["id"]
        pointer = connector.find(f"./views/{view}/p")
        if pointer is None:
            continue
        svg_id = pointer.attrib.get("terminalId") or pointer.attrib["svgId"]
        if svg_id not in by_id:
            svg_id = pointer.attrib["svgId"]
        x, y = element_center(by_id[svg_id])
        result[connector_id] = ((x - vb[0]) * sx, (y - vb[1]) * sy)
    return result


def part_points() -> dict[tuple[str, str], tuple[float, float]]:
    points = {}
    for part in PARTS:
        for connector_id, (dx, dy) in pad_offsets(part).items():
            points[(part.ref, connector_id)] = (part.x + dx, part.y + dy)
    return points


def pad_outer_radius(part: Part, connector_id: str) -> float:
    """Outer copper radius in Fritzing screen pixels."""
    if part.kind in {"jstxh3", "jstxh4", "jstxh5"}:
        return 0.90 * DPI / 25.4
    if part.kind == "terminal2":
        return 1.00 * DPI / 25.4
    if part.kind == "bc547":
        return 0.90 * DPI / 25.4
    kind = KINDS[part.kind]
    fzp = ET.parse(CORE / kind.fzp).getroot()
    image = fzp.find("./views/pcbView/layers").attrib["image"]
    svg = ET.parse(svg_path(image)).getroot()
    width = length_px(svg.attrib["width"])
    height = length_px(svg.attrib["height"])
    viewbox = [float(x) for x in svg.attrib.get("viewBox", f"0 0 {width} {height}").replace(",", " ").split()]
    factor = width / viewbox[2]
    connector = fzp.find(f"./connectors/connector[@id='{connector_id}']")
    svg_id = connector.find("./views/pcbView/p").attrib["svgId"]
    element = next(node for node in svg.iter() if node.attrib.get("id") == svg_id)
    if element.tag.endswith("rect"):
        return max(float(element.attrib["width"]), float(element.attrib["height"])) * factor / 2
    return (float(element.attrib.get("r", "0")) + float(element.attrib.get("stroke-width", "0")) / 2) * factor


@dataclass(frozen=True)
class GridPoint:
    x: int
    y: int


@dataclass(frozen=True)
class RouteState:
    point: GridPoint
    layer: str


def grid_xy(point: tuple[float, float]) -> GridPoint:
    return GridPoint(round((point[0] - BOARD_X) / GRID), round((point[1] - BOARD_Y) / GRID))


def real_xy(point: GridPoint) -> tuple[float, float]:
    return BOARD_X + point.x * GRID, BOARD_Y + point.y * GRID


def neighbours(point: GridPoint):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        yield GridPoint(point.x + dx, point.y + dy)


def point_to_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    norm = dx * dx + dy * dy
    if norm == 0:
        return math.dist(point, start)
    fraction = max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / norm))
    return math.dist(point, (start[0] + fraction * dx, start[1] + fraction * dy))


def mount_center_px(x_mm: float, y_mm: float) -> tuple[float, float]:
    return BOARD_X + x_mm * DPI / 25.4, BOARD_Y + y_mm * DPI / 25.4


def astar(start: GridPoint, targets: set[GridPoint], blocked: set[GridPoint]) -> list[GridPoint]:
    min_x, max_x = 2, int(BOARD_W / GRID) - 2
    min_y, max_y = 2, int(BOARD_H / GRID) - 2
    queue = [(0.0, 0, start)]
    previous: dict[GridPoint, GridPoint] = {}
    cost = {start: 0}
    serial = 0
    while queue:
        _, _, current = heapq.heappop(queue)
        if current in targets:
            path = [current]
            while current != start:
                current = previous[current]
                path.append(current)
            return list(reversed(path))
        for nxt in neighbours(current):
            if not (min_x <= nxt.x <= max_x and min_y <= nxt.y <= max_y):
                continue
            if nxt in blocked and nxt not in targets:
                continue
            new_cost = cost[current] + 1
            if new_cost >= cost.get(nxt, 10**9):
                continue
            cost[nxt] = new_cost
            previous[nxt] = current
            heuristic = min(abs(nxt.x - goal.x) + abs(nxt.y - goal.y) for goal in targets)
            serial += 1
            heapq.heappush(queue, (new_cost + heuristic, serial, nxt))
    raise RuntimeError(f"No route from {start} to net tree")


def astar_two_layers(
    start: GridPoint,
    targets: set[RouteState],
    occupied: dict[str, set[GridPoint]],
    blocked_pads: set[GridPoint],
    tree: set[RouteState],
    foreign_pads: list[tuple[tuple[float, float], float]],
    foreign_vias: list[tuple[float, float]],
) -> list[RouteState]:
    """Route with plated through vias; a via has a deliberately high cost."""
    min_x, max_x = 2, int(BOARD_W / GRID) - 2
    min_y, max_y = 2, int(BOARD_H / GRID) - 2
    track_radius = TRACE_MILS * DPI / 2000
    clearance = 0.24 * DPI / 25.4
    via_radius = 0.70 * DPI / 25.4
    starts = [RouteState(start, "top"), RouteState(start, "bottom")]
    queue: list[tuple[float, int, RouteState]] = []
    previous: dict[RouteState, RouteState] = {}
    cost: dict[RouteState, float] = {}
    serial = 0
    for state in starts:
        cost[state] = 0
        heapq.heappush(queue, (0, serial, state))
        serial += 1
    while queue:
        _, _, current = heapq.heappop(queue)
        if current in targets:
            path = [current]
            while current not in starts:
                current = previous[current]
                path.append(current)
            return list(reversed(path))
        candidates = [(RouteState(point, current.layer), 1.0) for point in neighbours(current.point)]
        other = "bottom" if current.layer == "top" else "top"
        candidates.append((RouteState(current.point, other), 8.0))
        for nxt, step_cost in candidates:
            p = nxt.point
            if not (min_x <= p.x <= max_x and min_y <= p.y <= max_y):
                continue
            if p in blocked_pads and nxt not in tree and p != start:
                continue
            if p in occupied[nxt.layer] and nxt not in tree:
                continue
            position = real_xy(p)
            previous_position = real_xy(current.point)
            if any(point_to_segment(pad, previous_position, position) < radius + track_radius + clearance
                   for pad, radius in foreign_pads):
                continue
            if any(point_to_segment(via, previous_position, position) < via_radius + track_radius + clearance
                   for via in foreign_vias):
                continue
            if current.layer != nxt.layer:
                if any(math.dist(position, pad) < radius + via_radius + clearance
                       for pad, radius in foreign_pads):
                    continue
                if any(math.dist(position, real_xy(cell)) < via_radius + track_radius + clearance
                       for occupied_layer in occupied.values() for cell in occupied_layer):
                    continue
            new_cost = cost[current] + step_cost
            if new_cost >= cost.get(nxt, 10**9):
                continue
            cost[nxt] = new_cost
            previous[nxt] = current
            heuristic = min(abs(p.x - goal.point.x) + abs(p.y - goal.point.y) for goal in targets)
            serial += 1
            heapq.heappush(queue, (new_cost + heuristic, serial, nxt))
    raise RuntimeError(f"No two-layer route from {start} to net tree")


def collapse(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
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


@dataclass
class RoutedSegment:
    net: str
    layer: str
    start: tuple[float, float]
    end: tuple[float, float]
    start_terminal: tuple[str, str] | None = None
    end_terminal: tuple[str, str] | None = None


@dataclass(frozen=True)
class RoutedVia:
    net: str
    point: tuple[float, float]


def route_all(points: dict[tuple[str, str], tuple[float, float]]) -> tuple[list[RoutedSegment], list[RoutedVia]]:
    occupied = {"top": set(), "bottom": set()}
    pad_cells = {terminal: grid_xy(point) for terminal, point in points.items()}
    all_pad_cells = set(pad_cells.values())
    part_map = {part.ref: part for part in PARTS}
    terminal_net = {terminal: name for name, (_, terminals) in NETS.items() for terminal in terminals}
    pad_data = [(point, pad_outer_radius(part_map[terminal[0]], terminal[1]), terminal_net.get(terminal))
                for terminal, point in points.items()]
    mount_obstacles = [(mount_center_px(x, y), MOUNT_KEEPOUT_MM * DPI / 25.4)
                       for x, y in MOUNT_CENTERS_MM]
    segments: list[RoutedSegment] = []
    vias: list[RoutedVia] = []

    def append_pad_lead(net: str, layer: str, terminal: tuple[str, str], cell: GridPoint) -> None:
        pad = points[terminal]
        grid = real_xy(cell)
        if pad == grid:
            return
        # Orthogonal dogleg avoids a diagonal cutting the clearance corner of
        # an adjacent connector pad or trace.
        lead = collapse([pad, (pad[0], grid[1]), grid])
        for index, (a, b) in enumerate(zip(lead, lead[1:])):
            segments.append(RoutedSegment(net, layer, a, b, terminal if index == 0 else None, None))
    # Route the long, topology-sensitive buses before the power trees. Power
    # nets have many possible branches and can route around them more easily.
    priority = {
        "3V3_SENSOR": 211, "3V3_I2C": 205, "A0": 201, "D1_SCL": 200, "D2_SDA": 199, "D5_DHT": 198,
        "D0_OFF": 190, "D3_MENU": 190, "D4_SELECT": 190,
        "D6_FAN": 190, "D8_HEAT": 190, "D7_COMP": 190,
        "5V_RAW": 170,
        "GND_ENTRY": 120, "GND_LOGIC": 119, "GND_I2C": 118, "GND_DRIVE": 117,
        "3V3_ENTRY": 110, "3V3_I2C": 109, "5V_SSR": 100,
    }
    priority.update({name: 180 for name in NETS if name.startswith(("BASE_", "CTRL_"))})
    order = sorted(NETS, key=lambda name: (priority.get(name, 50), len(NETS[name][1])), reverse=True)
    for net_name in order:
        preferred, terminals = NETS[net_name]
        foreign_pads = [(point, radius) for point, radius, net in pad_data if net != net_name] + mount_obstacles
        first = terminals[0]
        first_cell = pad_cells[first]
        tree: set[RouteState] = {RouteState(first_cell, preferred), RouteState(first_cell, "bottom" if preferred == "top" else "top")}
        net_cells = {"top": {first_cell}, "bottom": {first_cell}}
        first_lead_added = False
        for terminal in terminals[1:]:
            start = pad_cells[terminal]
            try:
                path = astar_two_layers(
                    start, tree, occupied, all_pad_cells - {start}, tree,
                    foreign_pads, [via.point for via in vias if via.net != net_name],
                )
            except RuntimeError as exc:
                raise RuntimeError(f"Cannot route {net_name} terminal {terminal}: {exc}") from exc
            if not first_lead_added:
                for copper_layer in ("top", "bottom"):
                    append_pad_lead(net_name, copper_layer, first, first_cell)
                first_lead_added = True
            for copper_layer in ("top", "bottom"):
                append_pad_lead(net_name, copper_layer, terminal, start)
            run_layer = path[0].layer
            run_points = [real_xy(path[0].point)]
            for before, after in zip(path, path[1:]):
                if before.layer != after.layer:
                    run_points = collapse(run_points)
                    for a, b in zip(run_points, run_points[1:]):
                        segments.append(RoutedSegment(net_name, run_layer, a, b))
                    via_point = real_xy(before.point)
                    vias.append(RoutedVia(net_name, via_point))
                    run_layer = after.layer
                    run_points = [via_point]
                else:
                    run_points.append(real_xy(after.point))
            run_points = collapse(run_points)
            for a, b in zip(run_points, run_points[1:]):
                segments.append(RoutedSegment(net_name, run_layer, a, b))
            for state in path:
                tree.add(state)
                net_cells[state.layer].add(state.point)
            # A through-hole terminal itself joins both copper layers.
            tree.add(RouteState(start, "top"))
            tree.add(RouteState(start, "bottom"))
            net_cells["top"].add(start)
            net_cells["bottom"].add(start)
        occupied["top"].update(net_cells["top"])
        occupied["bottom"].update(net_cells["bottom"])

    # Split each straight track where another branch ends on its interior.
    # Fritzing's connectivity graph requires explicit wire endpoints at T joins.
    junctions: dict[tuple[str, str], set[tuple[float, float]]] = defaultdict(set)
    for segment in segments:
        junctions[(segment.net, segment.layer)].add((round(segment.start[0], 4), round(segment.start[1], 4)))
        junctions[(segment.net, segment.layer)].add((round(segment.end[0], 4), round(segment.end[1], 4)))
    for via in vias:
        for layer in ("top", "bottom"):
            junctions[(via.net, layer)].add((round(via.point[0], 4), round(via.point[1], 4)))
    split: list[RoutedSegment] = []
    for segment in segments:
        ax, ay = segment.start
        bx, by = segment.end
        length_sq = (bx - ax) ** 2 + (by - ay) ** 2
        if length_sq < 1e-10:
            continue
        cuts = []
        for px, py in junctions[(segment.net, segment.layer)]:
            fraction = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / length_sq
            if not 1e-7 < fraction < 1 - 1e-7:
                continue
            if point_to_segment((px, py), segment.start, segment.end) < 1e-3:
                cuts.append((fraction, (px, py)))
        chain = [segment.start] + [point for _, point in sorted(cuts)] + [segment.end]
        for index, (start, end) in enumerate(zip(chain, chain[1:])):
            split.append(RoutedSegment(
                segment.net, segment.layer, start, end,
                segment.start_terminal if index == 0 else None,
                segment.end_terminal if index == len(chain) - 2 else None,
            ))
    segments = split

    # Associate a terminal at the free end of every routed branch.
    terminal_at = {tuple(round(value, 4) for value in point): terminal for terminal, point in points.items()}
    for segment in segments:
        if segment.start_terminal is None:
            segment.start_terminal = terminal_at.get(tuple(round(value, 4) for value in segment.start))
        segment.end_terminal = terminal_at.get(tuple(round(value, 4) for value in segment.end))
    return segments, vias


def add_connector_nodes(parent: ET.Element, count: int, layer: str) -> None:
    connectors = ET.SubElement(parent, "connectors")
    for number in range(count):
        node = ET.SubElement(connectors, "connector", connectorId=f"connector{number}", layer=layer)
        ET.SubElement(node, "geometry", x="0", y="0")
        ET.SubElement(node, "connects")


def make_part_instance(part: Part, index: str, z: float) -> ET.Element:
    kind = KINDS[part.kind]
    instance = ET.Element("instance", moduleIdRef=kind.module, modelIndex=index, path=kind.path)
    for name, value in part.properties.items():
        ET.SubElement(instance, "property", name=name, value=value)
    ET.SubElement(instance, "title").text = part.ref
    views = ET.SubElement(instance, "views")
    for view_name, layer, dz in (("breadboardView", "breadboard", 0), ("pcbView", "copper1", 0.1), ("schematicView", "schematic", 0.2)):
        view = ET.SubElement(views, view_name, layer=layer)
        ET.SubElement(view, "geometry", z=f"{z + dz:.4f}", x=f"{part.x:.4f}", y=f"{part.y:.4f}")
        title = ET.SubElement(view, "titleGeometry", visible="true", x=f"{part.x:.4f}", y=f"{part.y - 7:.4f}", z=f"{z + dz + 0.01:.4f}", xOffset="0", yOffset="-7", textColor="#000000", fontSize="4")
        ET.SubElement(title, "displayKey", key="")
        add_connector_nodes(view, part.connectors, layer)
    return instance


def connect_node(node: ET.Element, connector_id: str, target_index: str, target_connector: str, target_layer: str) -> None:
    connector = node.find(f"./connectors/connector[@connectorId='{connector_id}']")
    connects = connector.find("connects")
    ET.SubElement(connects, "connect", connectorId=target_connector, modelIndex=target_index, layer=target_layer)


def make_wire(index: str, segment: RoutedSegment, z: float) -> ET.Element:
    instance = ET.Element("instance", moduleIdRef="WireModuleID", modelIndex=index, path=":/resources/parts/core/wire.fzp")
    ET.SubElement(instance, "title").text = f"{segment.net}_{index}"
    views = ET.SubElement(instance, "views")
    x1, y1 = segment.start
    x2, y2 = segment.end
    for view_name, layer, mils, color, wire_flags in (
        ("breadboardView", "breadboardWire", TRACE_MILS, "#404040", "64"),
        ("pcbView", "copper1trace" if segment.layer == "top" else "copper0trace", TRACE_MILS, "#f28a00" if segment.layer == "top" else "#2f7ed8", "4"),
        ("schematicView", "schematicTrace", 10.0, "#404040", "128"),
    ):
        attrs = {"layer": layer}
        if view_name == "pcbView" and segment.layer == "bottom":
            attrs["bottom"] = "true"
        view = ET.SubElement(views, view_name, **attrs)
        ET.SubElement(view, "geometry", z=f"{z:.4f}", x=f"{x1:.4f}", y=f"{y1:.4f}", x1="0", y1="0", x2=f"{x2 - x1:.4f}", y2=f"{y2 - y1:.4f}", wireFlags=wire_flags)
        ET.SubElement(view, "wireExtras", mils=f"{mils:.4f}", color=color, opacity="1", banded="0")
        add_connector_nodes(view, 2, layer)
    return instance


def make_via(index: str, via: RoutedVia, z: float) -> ET.Element:
    instance = ET.Element(
        "instance", moduleIdRef="ThermostatViaModuleID", modelIndex=index,
        path="/home/ignacia/thermostat/thermostat_via.fzp",
    )
    ET.SubElement(instance, "title").text = f"VIA_{via.net}_{index}"
    views = ET.SubElement(instance, "views")
    view = ET.SubElement(views, "pcbView", layer="copper0")
    # The custom SVG is 1.4 mm square (4.9606 px at 90 dpi); center it.
    x, y = via.point
    ET.SubElement(view, "geometry", z=f"{z:.4f}", x=f"{x - 2.4803:.4f}", y=f"{y - 2.4803:.4f}")
    add_connector_nodes(view, 1, "copper0")
    return instance


def make_mount(index: str, ref: str, x_mm: float, y_mm: float) -> ET.Element:
    instance = ET.Element(
        "instance", moduleIdRef="ThermostatMountingHole3mm", modelIndex=index,
        path="/home/ignacia/thermostat/thermostat_mount.fzp",
    )
    ET.SubElement(instance, "title").text = ref
    views = ET.SubElement(instance, "views")
    view = ET.SubElement(views, "pcbView", layer="copper1")
    x, y = mount_center_px(x_mm, y_mm)
    half = 3.5 * DPI / 25.4
    ET.SubElement(view, "geometry", z="9.5", x=f"{x - half:.4f}", y=f"{y - half:.4f}")
    return instance


def endpoint_key(point: tuple[float, float]) -> tuple[float, float]:
    return round(point[0], 4), round(point[1], 4)


def build_xml() -> bytes:
    root = ET.Element("module", fritzingVersion="1.0.1", icon=".png")
    boards = ET.SubElement(root, "boards")
    ET.SubElement(boards, "board", moduleId="TwoLayerRectanglePCBModuleID", title="Rectangular PCB - Resizable", instance="PCB1", width=f"{BOARD_W_MM}mm", height=f"{BOARD_H_MM}mm")
    views = ET.SubElement(root, "views")
    ET.SubElement(views, "view", name="breadboardView", backgroundColor="#ffffff", gridSize="0.1in", showGrid="1", alignToGrid="1", viewFromBelow="0")
    ET.SubElement(views, "view", name="schematicView", backgroundColor="#ffffff", gridSize="0.1in", showGrid="1", alignToGrid="1", viewFromBelow="0")
    ET.SubElement(views, "view", name="pcbView", backgroundColor="#333333", gridSize="0.05in", showGrid="1", alignToGrid="1", viewFromBelow="0", GPG_Keepout="", autorouteViaHoleSize="", DRC_Keepout="", autorouteViaRingThickness="", autorouteTraceWidth=str(int(TRACE_MILS)))
    instance_list = ET.SubElement(root, "instances")

    board = ET.SubElement(instance_list, "instance", moduleIdRef="TwoLayerRectanglePCBModuleID", modelIndex="1", path=":/resources/parts/core/rectangle_pcb_two_layers.fzp")
    ET.SubElement(board, "property", name="layers", value="2")
    ET.SubElement(board, "property", name="width", value=str(BOARD_W_MM))
    ET.SubElement(board, "property", name="height", value=str(BOARD_H_MM))
    ET.SubElement(board, "title").text = "THERMOSTAT UNIVERSAL SELV ONLY REV-A"
    board_views = ET.SubElement(board, "views")
    ET.SubElement(ET.SubElement(board_views, "breadboardView", layer=""), "geometry", z="0.5", x="0", y="0")
    ET.SubElement(ET.SubElement(board_views, "pcbView", layer="board"), "geometry", z="1.5", x=str(BOARD_X), y=str(BOARD_Y))
    ET.SubElement(ET.SubElement(board_views, "schematicView", layer=""), "geometry", z="0.5", x="0", y="0")

    part_indices = {}
    part_instances = {}
    for number, part in enumerate(PARTS, start=100):
        index = str(number)
        part_indices[part.ref] = index
        instance = make_part_instance(part, index, 2.0 + number / 1000)
        instance_list.append(instance)
        part_instances[part.ref] = instance

    for number, (x_mm, y_mm) in enumerate(MOUNT_CENTERS_MM, start=1):
        instance_list.append(make_mount(str(9000 + number), f"H{number}", x_mm, y_mm))

    points = part_points()
    routed, vias = route_all(points)
    wire_instances = {}
    node_endpoints: dict[tuple[str, tuple[float, float]], list[tuple[str, str]]] = defaultdict(list)
    terminal_endpoints: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for number, segment in enumerate(routed, start=1000):
        index = str(number)
        wire = make_wire(index, segment, 5.0 + number / 10000)
        instance_list.append(wire)
        wire_instances[index] = wire
        node_endpoints[(segment.net, endpoint_key(segment.start))].append((index, "connector0"))
        node_endpoints[(segment.net, endpoint_key(segment.end))].append((index, "connector1"))
        if segment.start_terminal:
            terminal_endpoints[segment.start_terminal].append((index, "connector0"))
        if segment.end_terminal:
            terminal_endpoints[segment.end_terminal].append((index, "connector1"))

    via_instances = {}
    unique_vias = list(dict.fromkeys(vias))
    for number, via in enumerate(unique_vias, start=8000):
        index = str(number)
        instance = make_via(index, via, 8.0 + number / 10000)
        instance_list.append(instance)
        via_instances[index] = (instance, via)

    # Link coincident wire endpoints in every view.
    for endpoints in node_endpoints.values():
        if len(endpoints) < 2:
            continue
        for wire_index, connector_id in endpoints:
            wire = wire_instances[wire_index]
            for other_index, other_connector in endpoints:
                if (wire_index, connector_id) == (other_index, other_connector):
                    continue
                for view_name, layer in (("breadboardView", "breadboardWire"), ("pcbView", wire.find("./views/pcbView").attrib["layer"]), ("schematicView", "schematicTrace")):
                    view = wire.find(f"./views/{view_name}")
                    connect_node(view, connector_id, other_index, other_connector, layer)

    # Link part terminals to wire endpoints in both directions.
    for terminal, endpoints in terminal_endpoints.items():
        ref, connector_id = terminal
        part = part_instances[ref]
        part_index = part_indices[ref]
        for wire_index, wire_connector in endpoints:
            wire = wire_instances[wire_index]
            for view_name, part_layer, wire_layer in (
                ("breadboardView", "breadboard", "breadboardWire"),
                ("pcbView", "copper1", wire.find("./views/pcbView").attrib["layer"]),
                ("schematicView", "schematic", "schematicTrace"),
            ):
                part_view = part.find(f"./views/{view_name}")
                wire_view = wire.find(f"./views/{view_name}")
                connect_node(part_view, connector_id, wire_index, wire_connector, wire_layer)
                connect_node(wire_view, wire_connector, part_index, connector_id, part_layer)

    # Join every copper-layer transition to a real plated through via.
    for via_index, (via_instance, via) in via_instances.items():
        endpoints = node_endpoints[(via.net, endpoint_key(via.point))]
        via_view = via_instance.find("./views/pcbView")
        for wire_index, wire_connector in endpoints:
            wire = wire_instances[wire_index]
            wire_view = wire.find("./views/pcbView")
            wire_layer = wire_view.attrib["layer"]
            connect_node(via_view, "connector0", wire_index, wire_connector, wire_layer)
            connect_node(wire_view, wire_connector, via_index, "connector0", "copper0")

    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_fzz(output: Path, xml: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{output.name}.", dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("thermostat_universal.fz", xml)
            archive.writestr("part.thermostat_via.fzp", VIA_FZP)
            archive.writestr("svg.pcb.thermostat_via_pcb.svg", VIA_PCB_SVG)
            archive.writestr("svg.icon.thermostat_via_icon.svg", VIA_ICON_SVG)
            archive.writestr("part.thermostat_mount.fzp", MOUNT_FZP)
            archive.writestr("svg.pcb.thermostat_mount_pcb.svg", MOUNT_PCB_SVG)
            archive.writestr("svg.icon.thermostat_mount_icon.svg", MOUNT_ICON_SVG)
            for pins, assets in JST_ASSETS.items():
                base = f"thermostat_jstxh{pins}"
                archive.writestr(f"part.{base}.fzp", assets["fzp"])
                archive.writestr(f"svg.pcb.{base}_pcb.svg", assets["pcb"])
                archive.writestr(f"svg.breadboard.{base}_breadboard.svg", assets["breadboard"])
                archive.writestr(f"svg.icon.{base}_icon.svg", assets["icon"])
                archive.writestr(f"svg.schematic.{base}_schematic.svg", assets["schematic"])
            archive.writestr("part.thermostat_mkds2.fzp", TERMINAL_ASSETS["fzp"])
            for view in ("pcb", "breadboard", "icon", "schematic"):
                suffix = "pcb" if view == "pcb" else view
                archive.writestr(f"svg.{view}.thermostat_mkds2_{suffix}.svg", TERMINAL_ASSETS[view])
            archive.writestr("part.thermostat_bc547.fzp", BC547_ASSETS["fzp"])
            for view in ("pcb", "breadboard", "icon", "schematic"):
                archive.writestr(f"svg.{view}.thermostat_bc547_{view}.svg", BC547_ASSETS[view])
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("thermostat_universal.fzz"))
    args = parser.parse_args()
    xml = build_xml()
    write_fzz(args.output, xml)
    print(f"Built {args.output}: {BOARD_W_MM:.0f}x{BOARD_H_MM:.0f} mm, {len(PARTS)} parts, {len(NETS)} validated nets")


if __name__ == "__main__":
    main()
