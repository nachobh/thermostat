#!/usr/bin/env python3
"""Generate a PCBWay THT turn-key quote pack from the validated manual BOM.

The PCB is shared by manual and assembled variants.  This script never alters
the Fritzing design or manufacturing layers.  Fritzing's raw XY file labels F1
as SMT incorrectly, so all placements are explicitly classified THT here.
"""

from __future__ import annotations

import csv
from pathlib import Path

import build_universal_fzz as design


ROOT = Path(__file__).resolve().parent / "pcbway" / "thermostat_universal_rev_a"
MANUAL_BOM = ROOT / "BOM_MONTAJE_MANUAL.csv"
XY_SOURCE = ROOT / "thermostat_universal_pnp.xy"
PCBA_BOM = ROOT / "BOM_PCBWAY_TURNKEY.csv"
PLACEMENT = ROOT / "COLOCACION_THT_REFERENCIA.csv"


def main() -> None:
    with MANUAL_BOM.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    all_refs = {part.ref for part in design.PARTS}
    found: list[str] = []
    assembled: set[str] = set()
    bom_rows: list[dict[str, str]] = []
    for row in rows:
        refs = row["Referencias"].split()
        if len(refs) != int(row["Cantidad"]):
            raise SystemExit(f"Quantity mismatch: {row['Referencias']}")
        found.extend(refs)
        if row["Montaje"] != "SÍ":
            if row["Montaje"] != "DNP":
                raise SystemExit(f"Unknown assembly state: {row['Montaje']}")
            continue
        assembled.update(refs)
        specification = row["Referencia de compra o especificación"]
        bom_rows.append({
            "Line": str(len(bom_rows) + 1),
            "Quantity": str(len(refs)),
            "Designators": ", ".join(refs),
            "Description": row["Valor/función"],
            "Package/Footprint": row["Formato de la PCB"],
            "Type": "THT",
            "Manufacturer Part Number / Specification": specification,
            "Assembly": "POPULATE",
            "Notes": row["Observaciones"],
        })
    if len(found) != len(all_refs) or set(found) != all_refs:
        raise SystemExit("Manual BOM does not match design references exactly")
    if assembled != all_refs - {"R7", "R8", "R9"}:
        raise SystemExit("Unexpected PCBA population compared with DNP policy")

    with PCBA_BOM.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(bom_rows[0]))
        writer.writeheader()
        writer.writerows(bom_rows)

    with XY_SOURCE.open(newline="", encoding="utf-8") as handle:
        data = [line for line in handle if not line.startswith("#") and line.strip()]
    reader = csv.DictReader(data)
    raw_positions = {row["RefDes"]: row for row in reader if row["RefDes"] in assembled}
    if set(raw_positions) != assembled:
        raise SystemExit(f"Missing positions: {assembled - set(raw_positions)}")
    place_rows = []
    for ref in sorted(assembled, key=lambda item: (item[0], int(item[1:]))):
        pos = raw_positions[ref]
        if pos["Side"] != "Top":
            raise SystemExit(f"Unexpected assembly side for {ref}: {pos['Side']}")
        place_rows.append({
            "Designator": ref,
            "X_mm_from_left": f"{float(pos['X']) * 0.0254:.3f}",
            "Y_mm_from_bottom": f"{float(pos['Y']) * 0.0254:.3f}",
            "Side": "Top",
            "Technology": "THT",
            "Orientation": "See silkscreen and assembly instructions; raw Fritzing rotation is not authoritative",
        })
    with PLACEMENT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(place_rows[0]))
        writer.writeheader()
        writer.writerows(place_rows)

    print(f"Generated {len(bom_rows)} BOM lines and {len(place_rows)} THT placements; DNP: R7 R8 R9")


if __name__ == "__main__":
    main()
