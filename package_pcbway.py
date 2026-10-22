#!/usr/bin/env python3
"""Audit BOM, source and drill files; package only bare-PCB manufacturing layers."""

import csv
import math
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import build_universal_fzz as board


ROOT = Path(__file__).resolve().parent / "pcbway" / "thermostat_universal_rev_a"
PREFIX = "thermostat_universal_"
SUFFIXES = (
    "contour.gm1",
    "copperBottom.gbl",
    "copperTop.gtl",
    "drill.txt",
    "maskBottom.gbs",
    "maskTop.gts",
    "silkBottom.gbo",
    "silkTop.gto",
)
DESTINATION = ROOT / "thermostat_universal_rev_a_GERBER.zip"


def main() -> None:
    sources = [ROOT / (PREFIX + suffix) for suffix in SUFFIXES]
    for path in sources:
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Missing or empty manufacturing layer: {path}")
    source_fzz = Path(__file__).resolve().parent / "thermostat_universal.fzz"
    packaged_fzz = ROOT / "thermostat_universal.fzz"
    if source_fzz.read_bytes() != packaged_fzz.read_bytes():
        raise SystemExit("The Fritzing source copied into pcbway/ is stale")
    for path in sources:
        if path.stat().st_mtime_ns < packaged_fzz.stat().st_mtime_ns:
            raise SystemExit(f"Gerber/Excellon predates the current Fritzing file: {path.name}")

    bom_refs = []
    with (ROOT / "BOM_MONTAJE_MANUAL.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            refs = row["Referencias"].split()
            if len(refs) != int(row["Cantidad"]):
                raise SystemExit(f"BOM quantity disagrees with references: {refs}")
            bom_refs.extend(refs)
    design_refs = {part.ref for part in board.PARTS}
    if len(bom_refs) != len(design_refs) or set(bom_refs) != design_refs:
        raise SystemExit(f"BOM differs from Fritzing design: missing={design_refs - set(bom_refs)}, extra={set(bom_refs) - design_refs}")

    pcba_refs = []
    with (ROOT / "BOM_PCBWAY_TURNKEY.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            refs = [ref.strip() for ref in row["Designators"].split(",")]
            if len(refs) != int(row["Quantity"]) or row["Type"] != "THT" or row["Assembly"] != "POPULATE":
                raise SystemExit(f"Invalid turn-key BOM line: {row}")
            pcba_refs.extend(refs)
    expected_pcba = design_refs - {"R7", "R8", "R9"}
    if len(pcba_refs) != len(expected_pcba) or set(pcba_refs) != expected_pcba:
        raise SystemExit("Turn-key BOM does not match populated design references")
    with (ROOT / "COLOCACION_THT_REFERENCIA.csv").open(newline="", encoding="utf-8-sig") as handle:
        positions = list(csv.DictReader(handle))
    position_refs = [row["Designator"] for row in positions]
    if len(position_refs) != len(expected_pcba) or set(position_refs) != expected_pcba:
        raise SystemExit("THT placement table does not match turn-key BOM")
    if any(row["Side"] != "Top" or row["Technology"] != "THT" for row in positions):
        raise SystemExit("Unexpected PCBWay assembly side or technology")

    drill = (ROOT / (PREFIX + "drill.txt")).read_text(encoding="ascii")
    hole_count = sum(line.startswith("X") for line in drill.splitlines())
    pad_count = len(board.part_points())
    if hole_count < pad_count + len(board.MOUNT_CENTERS_MM):
        raise SystemExit(f"Excellon has fewer holes ({hole_count}) than pads ({pad_count})")
    nonplated = []
    tool = None
    for line in drill.splitlines():
        if line == "T1":
            tool = "T1"
        elif re.fullmatch(r"T\d+", line):
            tool = line
        elif tool == "T1" and line.startswith("X"):
            match = re.fullmatch(r"X(\d+)Y(\d+)", line)
            if match is None:
                raise SystemExit(f"Invalid mounting-hole coordinate: {line}")
            nonplated.append((int(match.group(1)) / 10000 * 25.4,
                              int(match.group(2)) / 10000 * 25.4))
    diameter = re.search(r"^T1C([0-9.]+)$", drill, re.MULTILINE)
    if diameter is None or not math.isclose(float(diameter.group(1)) * 25.4,
                                             board.MOUNT_DRILL_MM, abs_tol=0.01):
        raise SystemExit("Excellon is missing the exact 3.0 mm NPTH tool")
    if len(nonplated) != len(board.MOUNT_CENTERS_MM):
        raise SystemExit(f"Expected four NPTH mounting holes, got {len(nonplated)}")
    for actual, expected in zip(sorted(nonplated), sorted(board.MOUNT_CENTERS_MM)):
        if math.dist(actual, expected) > 0.01:
            raise SystemExit(f"Mounting-hole position mismatch: {actual} != {expected}")
    with ZipFile(DESTINATION, "w", ZIP_DEFLATED) as archive:
        for path in sources:
            archive.write(path, path.name)
    with ZipFile(DESTINATION) as archive:
        if sorted(archive.namelist()) != sorted(path.name for path in sources):
            raise SystemExit("Unexpected files in fabrication ZIP")
        for path in sources:
            if archive.read(path.name) != path.read_bytes():
                raise SystemExit(f"Corrupt or stale ZIP layer: {path.name}")
    print(f"Audited {len(design_refs)} manual BOM parts, {len(expected_pcba)} PCBA parts, {pad_count} pads, {len(nonplated)} NPTH mounts and {hole_count} drill hits")
    print(f"Packaged {len(sources)} Gerber/Excellon files: {DESTINATION}")


if __name__ == "__main__":
    main()
