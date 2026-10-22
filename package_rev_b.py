#!/usr/bin/env python3
"""Export and package Rev B for PCBWay and JLCPCB.

1. Exports Gerber/Excellon/XY from thermostat_rev_b.fzz with headless Fritzing.
2. Audits the drill file against the design (pads, vias, 4 x NPTH 3.2 mm).
3. Writes the Gerber ZIP (same file for PCBWay and JLCPCB), the BOM and
   centroid files for both fabs, a Spanish manual BOM and preview images.
Run validate_rev_b.py first; this script does not re-check clearances.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import math
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

_parser = argparse.ArgumentParser()
_parser.add_argument("--design", default="build_rev_b_fzz", help="generator module (build_rev_b_fzz, build_rev_c_fzz)")
design = importlib.import_module(_parser.parse_args().design)
REV_C = design.SKETCH.endswith("rev_c")
REV = "C" if REV_C else "B"

HERE = Path(__file__).resolve().parent
OUT = HERE / "pcbway" / design.SKETCH
GERBER_DIR = OUT / "gerber"
SKETCH = design.SKETCH
LAYERS = ("contour.gm1", "copperBottom.gbl", "copperTop.gtl", "drill.txt", "maskBottom.gbs",
          "maskTop.gts", "pasteMaskTop.gtp", "silkBottom.gbo", "silkTop.gto") + (("pasteMaskBottom.gbp",) if REV_C else ())
# Fitted by hand at JLCPCB: the mains terminal and TR5 fuse have no LCSC stock code, nor do
# the NodeMCU sockets (Rev B also leaves the row choice to the user).
HAND_SOLDER_JLC = {"U1", "J20", "F2"}


def run(cmd: list[str], **kwargs) -> None:
    subprocess.run(cmd, check=True, **kwargs)


def export_gerbers() -> None:
    with tempfile.TemporaryDirectory(prefix="rev_b_export_") as tmp:
        tmp_path = Path(tmp)
        shutil.copy2(HERE / f"{SKETCH}.fzz", tmp_path / f"{SKETCH}.fzz")
        log = OUT / "fritzing_export.log"
        with log.open("w") as handle:
            run(["timeout", "300", "xvfb-run", "-a", "fritzing", "-gerber", str(tmp_path)],
                stdout=handle, stderr=subprocess.STDOUT)
        GERBER_DIR.mkdir(parents=True, exist_ok=True)
        for suffix in LAYERS + ("pnp.xy",):
            if suffix == "pasteMaskBottom.gbp":
                continue          # Fritzing does not export it; written by write_bottom_paste()
            source = tmp_path / f"{SKETCH}_{suffix}"
            if suffix == "pasteMaskTop.gtp" and not source.exists():
                (GERBER_DIR / source.name).unlink(missing_ok=True)
                continue          # no SMD on the top side (Rev C): no top paste layer
            if not source.is_file() or source.stat().st_size == 0:
                raise SystemExit(f"Fritzing did not export {source.name}")
            shutil.copy2(source, GERBER_DIR / source.name)
    shutil.copy2(HERE / f"{SKETCH}.fzz", OUT / f"{SKETCH}.fzz")


def clean_top_paste() -> int:
    """Fritzing flashes paste on the unplated mounting holes; drop that aperture."""
    path = GERBER_DIR / f"{SKETCH}_pasteMaskTop.gtp"
    if not path.exists():
        return 0
    lines = path.read_text(encoding="ascii").splitlines()
    hole = f"{design.MOUNT_DRILL_MM / 25.4:.6f}"
    tools = {m.group(1) for line in lines if (m := re.fullmatch(r"%ADD(\d+)C,([0-9.]+)\*%", line))
             and math.isclose(float(m.group(2)), float(hole), abs_tol=1e-4)}
    out, current, removed = [], None, 0
    for line in lines:
        m = re.fullmatch(r"(?:G54)?D(\d+)\*", line)
        if m:
            current = m.group(1)
        if current in tools and line.endswith("D03*"):
            removed += 1
            continue
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="ascii")
    return removed


def write_bottom_paste() -> int:
    """Paste layer for bottom-side SMD pads (Fritzing does not export it)."""
    pads = [(part.x + pad.x, part.y + pad.y, pad.w, pad.h) for part in design.PARTS
            for pad in part.fp.pads if pad.smd and getattr(pad, "bottom", False) and not pad.name.startswith("F")]
    apertures = {}
    body = []
    for x, y, w, h in pads:
        key = (round(w / 25.4, 6), round(h / 25.4, 6))
        code = apertures.setdefault(key, 10 + len(apertures))
        body.append((code, round(x / 25.4 * 1000), round((design.BOARD_H_MM - y) / 25.4 * 1000)))
    lines = ["G04 PASTE BOTTOM - written by package_rev_b.py (bottom-side SMD pads)*", "%ASAXBY*%", "%FSLAX23Y23*%",
             "%MOIN*%", "%OFA0B0*%", "%SFA1.0B1.0*%"]
    lines += [f"%ADD{code}R,{w:.6f}X{h:.6f}*%" for (w, h), code in apertures.items()]
    lines += ["%LNPASTEMASK0*%", "G90*", "G70*"]
    for code in sorted(set(c for c, _, _ in body)):
        lines.append(f"D{code}*")
        lines += [f"X{x}Y{y}D03*" for c, x, y in body if c == code]
    lines += ["M02*"]
    (GERBER_DIR / f"{SKETCH}_pasteMaskBottom.gbp").write_text("\n".join(lines) + "\n", encoding="ascii")
    return len(body)


def append_bottom_silk() -> int:
    """Outline and pin-1 mark of bottom-side parts (Fritzing drops their silkscreen0)."""
    path = GERBER_DIR / f"{SKETCH}_silkBottom.gbo"
    text = path.read_text(encoding="ascii").rstrip()
    assert text.endswith("M02*")
    if hasattr(design, "bottom_silk"):
        strokes = design.bottom_silk()
    else:
        strokes = [[(part.x + x, part.y + y) for x, y in line] for part in design.PARTS
                   if getattr(part.fp, "bottom", False) for line in part.fp.silk]
    mil = lambda v: round(v / 25.4 * 1000)
    out = ["%ADD90C,0.006000*%", "G54D90*"]
    for line in strokes:
        (x0, y0), rest = line[0], line[1:]
        out.append(f"X{mil(x0)}Y{mil(design.BOARD_H_MM - y0)}D02*")
        out += [f"X{mil(x)}Y{mil(design.BOARD_H_MM - y)}D01*" for x, y in rest]
    body = text[: -len("M02*")].rstrip()
    path.write_text(body + "\n" + "\n".join(out) + "\nM02*\n", encoding="ascii")
    return len(strokes)


def audit_bottom_pads() -> int:
    """Every bottom-side SMD pad must be flashed on the bottom copper exactly where the design has it."""
    text = (GERBER_DIR / f"{SKETCH}_copperBottom.gbl").read_text(encoding="ascii").splitlines()
    apertures = {m.group(1): m.group(2) for line in text if (m := re.fullmatch(r"%ADD(\d+)(\S+)\*%", line))}
    flashes, current = [], None
    for line in text:
        m = re.fullmatch(r"(?:G54)?D(\d+)\*", line)
        if m:
            current = m.group(1)
            continue
        m = re.fullmatch(r"X(\d+)Y(\d+)D03\*", line)
        if m and current and apertures[current].startswith("R,"):
            flashes.append((int(m.group(1)) * 0.0254, design.BOARD_H_MM - int(m.group(2)) * 0.0254))
    expected = [(part.x + pad.x, part.y + pad.y, f"{part.ref}.{pad.name}") for part in design.PARTS
                for pad in part.fp.pads if pad.smd and getattr(pad, "bottom", False)]
    for x, y, name in expected:
        if not any(math.dist((x, y), f) < 0.03 for f in flashes):
            raise SystemExit(f"Bottom pad {name} not found at ({x:.2f}, {y:.2f}) in the exported copper")
    if len(flashes) != len(expected):
        raise SystemExit(f"{len(flashes)} rectangular pads on the bottom copper, design has {len(expected)}")
    return len(expected)


def audit_drill(vias: int) -> str:
    drill = (GERBER_DIR / f"{SKETCH}_drill.txt").read_text(encoding="ascii")
    tools, current, hits = {}, None, {}
    for line in drill.splitlines():
        match = re.fullmatch(r"T(\d+)C([0-9.]+)", line)
        if match:
            tools[match.group(1)] = float(match.group(2)) * 25.4
            continue
        if re.fullmatch(r"T\d+", line):
            current = line[1:]
            continue
        match = re.fullmatch(r"X(\d+)Y(\d+)", line)
        if match and current:
            hits.setdefault(current, []).append((int(match.group(1)) / 10000 * 25.4,
                                                 int(match.group(2)) / 10000 * 25.4))
    tht = sum(1 for part in design.PARTS for pad in part.fp.pads if not pad.smd)
    plated = sum(len(v) for t, v in hits.items() if t != "1")
    if plated != tht + vias:
        raise SystemExit(f"Plated holes {plated} != THT pads {tht} + vias {vias}")
    if not math.isclose(tools["1"], design.MOUNT_DRILL_MM, abs_tol=0.02):
        raise SystemExit(f"NPTH tool is {tools['1']:.3f} mm")
    expected = sorted((x, design.BOARD_H_MM - y) for x, y in design.MOUNT_CENTERS_MM)
    for actual, wanted in zip(sorted(hits["1"]), expected):
        if math.dist(actual, wanted) > 0.02:
            raise SystemExit(f"Mounting hole at {actual} instead of {wanted}")
    by_size = {f"{tools[t]:.2f} mm": len(v) for t, v in sorted(hits.items(), key=lambda kv: tools[kv[0]])}
    return f"{plated} plated holes ({tht} pads + {vias} vias), 4 NPTH {design.MOUNT_DRILL_MM} mm; tools {by_size}"


def bom_groups() -> list[tuple[dict, str, list[design.Part]]]:
    groups: OrderedDict[tuple, list[design.Part]] = OrderedDict()
    for part in design.PARTS:
        groups.setdefault(part.bom["mpn"], []).append(part)
    order = lambda ref: (re.sub(r"\d+", "", ref), int(re.sub(r"\D", "", ref) or 0))
    result = []
    for parts in groups.values():
        values = {p.value for p in parts}
        value = values.pop() if len(values) == 1 else parts[0].bom["mpn"].split(" (")[0]
        result.append((parts[0].bom, value, sorted(parts, key=lambda p: order(p.ref))))
    return result


def footprint_name(part: design.Part) -> str:
    key = part.fp.key.removesuffix("_bot")
    return {
        "rb_0805_res": "R0805", "rb_0805_cap": "C0805", "rb_sot23_npn": "SOT-23-3",
        "rb_sod123_r180": "SOD-123", "rb_1812_ptc": "1812", "rb_hf115f": "Relay_THT_HF115F-1ZS3",
        "rb_tr5": "Fuse_TR5_P5.08mm", "rb_radial63": "CP_Radial_D6.3mm_P2.50mm",
        "rb_nodemcu_dual": "2x PinSocket_1x15_P2.54mm", "rb_mkds4_mains": "TerminalBlock_P5.08mm_1x04",
        "rc_nodemcu_amica": "2x PinSocket_1x15_P2.54mm (rows 22.86 mm)", "rb_mkds4_mains_r90": "TerminalBlock_P5.08mm_1x04",
        "rb_tr5_r90": "Fuse_TR5_P5.08mm", "rb_0805_res_r270": "R0805", "rc_fpc50_afc07_bottom": "FPC_0.5mm_50P_AFC07 (bottom)",
        "rb_mkds2_selv": "TerminalBlock_P5.08mm_1x02",
        "rb_0805_res_r180": "R0805", "rb_0805_res_r90": "R0805", "rb_sot23_npn_r180": "SOT-23-3", "rb_sod123": "SOD-123",
    }.get(key, f"JST_XH_B{len(part.fp.pads)}B-XH-A_1x{len(part.fp.pads):02d}_P2.50mm_Vertical")


def write_csv(path: Path, rows: list[dict], bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig" if bom else "utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def centroid(part: design.Part) -> tuple[float, float]:
    return part.x, design.BOARD_H_MM - part.y


def write_assembly_files() -> tuple[int, int]:
    groups = bom_groups()
    jlc_bom, pcbway_bom, manual = [], [], []
    for number, (info, value, parts) in enumerate(groups, start=1):
        refs = [p.ref for p in parts]
        qty = len(parts) * (2 if info is design.BOM_INFO["socket15"] else 1)
        jlc_bom.append({"Comment": value, "Designator": ",".join(refs),
                        "Footprint": footprint_name(parts[0]),
                        "LCSC Part #": "" if set(refs) & HAND_SOLDER_JLC else info["lcsc"]})
        pcbway_bom.append({
            "Item #": number, "Designator": ",".join(refs), "Qty": qty, "Manufacturer": info["mfr"],
            "Mfg Part #": info["mpn"], "Description / Value": f"{value} - {info['desc']}",
            "Package/Footprint": footprint_name(parts[0]), "Type": info["type"],
            "Your Instructions / Notes": (
                "2 x 1x15 female headers in the two rows of U1 (22.86 mm apart, NodeMCU Amica)" if refs == ["U1"] and REV_C
                else "BOTTOM SIDE. Upper-contact FPC connector, opening towards the board's top edge (see silkscreen)" if refs == ["J6"]
                else "Do NOT assemble: customer solders the sockets (row choice depends on module)" if refs == ["U1"]
                else "Mains side: orientation per silkscreen; pin COM in the middle column" if refs[0].startswith("RL")
                else "BOTTOM SIDE. Diode: cathode bar towards +5V (see bottom silkscreen)" if refs[0].startswith("D") and REV_C
                else "BOTTOM SIDE (all SMD parts are on the bottom side)" if REV_C and getattr(parts[0].fp, "bottom", False)
                else "Diode: cathode bar to the right (towards +5V)" if refs[0].startswith("D")
                else "Electrolytic: + pad marked on silkscreen" if refs == ["C1"] else ""),
        })
        manual.append({
            "Línea": number, "Cantidad": qty, "Referencias": " ".join(refs), "Valor/función": value,
            "Fabricante": info["mfr"], "Referencia de compra": info["mpn"], "LCSC": info["lcsc"] or "—",
            "Tipo": info["type"], "Huella": footprint_name(parts[0]), "Descripción": info["desc"],
            "Montaje": "SÍ (cara inferior)" if refs == ["J6"] else "A MANO (zócalos)" if refs == ["U1"] and not REV_C else "SÍ",
        })
    write_csv(OUT / "jlcpcb" / "BOM_JLCPCB.csv", jlc_bom)
    write_csv(OUT / "pcbway" / "BOM_PCBWAY.csv", pcbway_bom, bom=True)
    write_csv(OUT / "BOM_MANUAL_ES.csv", manual, bom=True)

    cpl, pcbway_xy = [], []
    for part in sorted(design.PARTS, key=lambda p: (re.sub(r"\d+", "", p.ref), int(re.sub(r"\D", "", p.ref)))):
        x, y = centroid(part)
        rotation = part.fp.rotation % 360
        layer = "Bottom" if getattr(part.fp, "bottom", False) else "Top"
        if part.ref not in HAND_SOLDER_JLC:
            cpl.append({"Designator": part.ref, "Mid X": f"{x:.3f}mm", "Mid Y": f"{y:.3f}mm",
                        "Layer": layer, "Rotation": rotation})
        if part.ref != "U1" or REV_C:
            pcbway_xy.append({"Designator": part.ref, "Mid X(mm)": f"{x:.3f}", "Mid Y(mm)": f"{y:.3f}",
                              "Layer": layer, "Rotation": rotation,
                              "Type": "SMD" if part.fp.smd else "THT"})
    write_csv(OUT / "jlcpcb" / "CPL_JLCPCB.csv", cpl)
    write_csv(OUT / "pcbway" / "CENTROID_PCBWAY.csv", pcbway_xy, bom=True)

    # Cross-check our centroids with Fritzing's own pick-and-place output.
    rows = [line for line in (GERBER_DIR / f"{SKETCH}_pnp.xy").read_text().splitlines()
            if line and not line.startswith(("#", "Description"))]
    fritzing = {r["RefDes"]: r for r in csv.DictReader(rows)}
    worst = 0.0
    for part in design.PARTS:
        row = fritzing.get(part.ref)
        if row is None:
            raise SystemExit(f"Fritzing XY lacks {part.ref}")
        if getattr(part.fp, "bottom", False):
            continue          # Fritzing lists bottom parts as Top; our CPL marks them Bottom
        x0, y0, x1, y1 = part.fp.bbox()
        expected = (part.x + (x0 + x1) / 2, design.BOARD_H_MM - (part.y + (y0 + y1) / 2))
        actual = (float(row["X"]) * 0.0254, float(row["Y"]) * 0.0254)
        worst = max(worst, math.dist(expected, actual))
    if worst > 0.05:
        raise SystemExit(f"Fritzing placement differs from the design by {worst:.3f} mm")
    return len(jlc_bom), len(cpl)


def zip_gerbers() -> Path:
    destination = OUT / f"{SKETCH}_GERBER.zip"
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for suffix in LAYERS:
            path = GERBER_DIR / f"{SKETCH}_{suffix}"
            if path.exists():
                archive.write(path, path.name)
    return destination


def previews() -> None:
    g = GERBER_DIR / SKETCH
    run(["gerbv", "-x", "png", "-D", "300", "-B", "0", "-o", str(OUT / "VERIFICACION_TOP.png"), "-b", "#1b4d2e",
         f"{g}_contour.gm1", "--foreground=#ffffffff", f"{g}_silkTop.gto", "--foreground=#c8c8c8ff",
         f"{g}_maskTop.gts", "--foreground=#d4a017ff", f"{g}_copperTop.gtl", "--foreground=#000000ff",
         f"{g}_drill.txt"])
    run(["gerbv", "-x", "png", "-D", "300", "-B", "0", "-o", str(OUT / "VERIFICACION_BOTTOM.png"), "-b", "#1b4d2e",
         f"{g}_contour.gm1", "--foreground=#ffffffff", f"{g}_silkBottom.gbo", "--foreground=#c8c8c8ff",
         f"{g}_maskBottom.gbs", "--foreground=#4aa3ffff", f"{g}_copperBottom.gbl", "--foreground=#000000ff",
         f"{g}_drill.txt"])
    with tempfile.TemporaryDirectory(prefix="rev_b_svg_") as tmp:
        shutil.copy2(HERE / f"{SKETCH}.fzz", Path(tmp) / f"{SKETCH}.fzz")
        run(["timeout", "300", "xvfb-run", "-a", "fritzing", "-svg", tmp],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copy2(Path(tmp) / f"{SKETCH}_schematic.svg", OUT / f"ESQUEMA_REV_{REV}.svg")
        shutil.copy2(Path(tmp) / f"{SKETCH}_pcb.svg", OUT / f"PCB_REV_{REV}.svg")
    # ImageMagick's built-in SVG renderer drops Fritzing's compact paths; a browser does not.
    with tempfile.TemporaryDirectory(prefix="rev_b_ff_") as tmp:
        wrapper = Path(tmp) / "schematic.html"
        wrapper.write_text(f'<!doctype html><body style="margin:0;background:#fff">'
                           f'<img src="file://{OUT / f"ESQUEMA_REV_{REV}.svg"}" style="width:2000px;display:block">')
        run(["timeout", "120", "firefox", "--headless", "--no-remote", "--profile", tmp, "--window-size", "2000,1000",
             "--screenshot", str(OUT / f"ESQUEMA_REV_{REV}.png"), f"file://{wrapper}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _, segments, vias = design.route_everything()
    write_target = HERE / f"{SKETCH}.fzz"
    design.write_fzz(write_target, design.build_xml(design.all_pad_points(), segments, vias))
    export_gerbers()
    print(f"Top paste: removed {clean_top_paste()} flashes on NPTH mounting holes")
    if REV_C:
        print(f"Bottom paste: {write_bottom_paste()} pads; bottom silk: {append_bottom_silk()} strokes")
        print(f"Bottom copper: all {audit_bottom_pads()} SMD pads exactly where the design has them")
        # Fritzing once duplicated bottom-side SMD pads onto the top copper: make sure it did not.
        fine = "R,0.011811X0.047244"
        top = (GERBER_DIR / f"{SKETCH}_copperTop.gtl").read_text(encoding="ascii")
        bottom = (GERBER_DIR / f"{SKETCH}_copperBottom.gbl").read_text(encoding="ascii")
        if fine in top or fine not in bottom or re.search(r"%ADD\d+R,", top):
            raise SystemExit("SMD pads found on the top copper: all SMD parts must be on the bottom only")
    print(audit_drill(len(vias)))
    bom_lines, placements = write_assembly_files()
    print(f"BOM lines: {bom_lines}; JLC placements: {placements} (hand: {', '.join(sorted(HAND_SOLDER_JLC))})")
    print(f"Gerber ZIP: {zip_gerbers()}")
    previews()
    print(f"Previews and schematic written to {OUT}")


if __name__ == "__main__":
    main()
