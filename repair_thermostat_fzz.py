#!/usr/bin/env python3
"""Repair the low-voltage thermostat carrier in sketch_pcb.fzz.

The mains wiring and the three panel-mount SSRs intentionally remain external.
The PCB exposes one 5 V control connector per SSR.  Running this script twice is
safe: the second run leaves already migrated parts unchanged.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


SSR_PART = "screw_terminal_2_200mil"
SSR_PATH = ":/resources/parts/core/screw_terminal_2_200mil.fzp"
NPN_PART = "SparkFun-DiscreteSemi-TRANSISTOR_NPN_2-PTH"
NPN_PATH = ":/resources/parts/core/sparkfun-discretesemi-transistor_npn_2-pth.fzp"
NODEMCU_INDEX = "7046"

SSR_CHANNELS = {
    "8601": "J_COMPRESSOR_SSR_5V",
    "8604": "J_HEATING_SSR_5V",
    "8606": "J_FAN_SSR_5V",
}

NPN_CHANNELS = {
    "20003": "Q_COMPRESSOR_BC547B_CBE",
    "20013": "Q_HEATING_BC547B_CBE",
    "20023": "Q_FAN_BC547B_CBE",
}

DRIVER_GROUND_WIRES = {
    "20003": "20008",
    "20013": "20018",
    "20023": "20028",
}

TITLE_RENAMES = {
    "1k FRIO": "1k COMPRESSOR",
    "10k FRIO": "10k COMPRESSOR",
    "100nF SSR FRIO": "100nF SSR COMPRESSOR",
    "1k CALOR": "1k HEATING",
    "10k CALOR": "10k HEATING",
    "100nF SSR CALOR": "100nF SSR HEATING",
    "1k VENT": "1k FAN",
    "10k VENT": "10k FAN",
    "100nF SSR VENT": "100nF SSR FAN",
    "4.7k SDA": "4.7k SDA OPTIONAL_DNP",
    "4.7k SCL": "4.7k SCL OPTIONAL_DNP",
}

PCB_POSITIONS = {
    "7046": (120, 35),
    "7053": (300, 115),
    "7240": (300, 15),
    "7243": (365, 15),
    "7352": (430, 65),
    "7733": (445, 145),
    "8472": (365, 115),
    "8490": (320, 180),
    "8496": (350, 180),
    "8601": (455, 225),
    "8604": (455, 270),
    "8606": (455, 315),
    "20001": (215, 225),
    "20002": (275, 225),
    "20003": (335, 225),
    "20004": (395, 225),
    "20011": (215, 270),
    "20012": (275, 270),
    "20013": (335, 270),
    "20014": (395, 270),
    "20021": (215, 315),
    "20022": (275, 315),
    "20023": (335, 315),
    "20024": (395, 315),
    "20031": (125, 300),
    "20034": (300, 75),
    "20037": (365, 75),
    "20040": (430, 115),
    "20043": (300, 155),
    "20046": (160, 300),
    "20049": (240, 80),
    "20052": (240, 100),
}


def view_layer(view_name: str) -> tuple[str, str]:
    if view_name == "breadboardView":
        return "breadboard", "breadboardWire"
    if view_name == "schematicView":
        return "schematic", "schematicTrace"
    return "copper0", "copper1trace"


def instances(root: ET.Element) -> dict[str, ET.Element]:
    return {node.attrib["modelIndex"]: node for node in root.findall(".//instance")}


def connector(instance: ET.Element, view_name: str, connector_id: str) -> ET.Element:
    view = instance.find(f"./views/{view_name}")
    if view is None:
        raise RuntimeError(f"{instance.findtext('title')} has no {view_name}")
    connectors = view.find("connectors")
    if connectors is None:
        connectors = ET.SubElement(view, "connectors")
    node = connectors.find(f"connector[@connectorId='{connector_id}']")
    if node is None:
        part_layer, _ = view_layer(view_name)
        node = ET.SubElement(connectors, "connector", connectorId=connector_id, layer=part_layer)
        ET.SubElement(node, "geometry", x="0", y="0")
        ET.SubElement(node, "connects")
    if node.find("connects") is None:
        ET.SubElement(node, "connects")
    return node


def remove_backlink(part: ET.Element, view_name: str, connector_id: str, wire_index: str) -> None:
    node = connector(part, view_name, connector_id)
    connects = node.find("connects")
    for link in list(connects):
        if link.attrib.get("modelIndex") == wire_index:
            connects.remove(link)


def add_backlink(part: ET.Element, view_name: str, connector_id: str, wire_index: str, wire_connector: str) -> None:
    node = connector(part, view_name, connector_id)
    connects = node.find("connects")
    _, wire_layer = view_layer(view_name)
    for link in connects:
        if link.attrib.get("modelIndex") == wire_index:
            link.attrib.update(connectorId=wire_connector, layer=wire_layer)
            return
    ET.SubElement(connects, "connect", connectorId=wire_connector, modelIndex=wire_index, layer=wire_layer)


def migrate_ssr(instance_map: dict[str, ET.Element], ssr_index: str, title: str) -> None:
    ssr = instance_map[ssr_index]
    if ssr.attrib.get("moduleIdRef") == SSR_PART:
        return

    # The old part uses connector2=IN+ and connector3=IN-.  On the new board
    # connector0 is +5V and connector1 is the NPN-switched negative terminal.
    for node in ssr.findall(".//connector"):
        old = node.attrib.get("connectorId")
        if old == "connector2":
            node.attrib["connectorId"] = "connector1"
        elif old == "connector3":
            node.attrib["connectorId"] = "connector0"

    for part in instance_map.values():
        for link in part.findall(".//connect"):
            if link.attrib.get("modelIndex") != ssr_index:
                continue
            if link.attrib.get("connectorId") == "connector2":
                link.attrib["connectorId"] = "connector1"
            elif link.attrib.get("connectorId") == "connector3":
                link.attrib["connectorId"] = "connector0"

    ssr.attrib.update(moduleIdRef=SSR_PART, path=SSR_PATH)
    ssr.find("title").text = title

    # The wire formerly tying SSR IN- to GND now supplies SSR+ from USB/Vin.
    for view_name in ("breadboardView", "pcbView", "schematicView"):
        jplus = connector(ssr, view_name, "connector0")
        links = list(jplus.find("connects"))
        if len(links) != 1:
            raise RuntimeError(f"{title} + terminal expected one wire, found {len(links)}")
        wire_index = links[0].attrib["modelIndex"]
        wire = instance_map[wire_index]
        wire_view = wire.find(f"./views/{view_name}")
        endpoints = list(wire_view.find("connectors"))
        ssr_endpoint = None
        supply_endpoint = None
        for endpoint in endpoints:
            target = endpoint.find("./connects/connect")
            if target is not None and target.attrib.get("modelIndex") == ssr_index:
                ssr_endpoint = endpoint
            else:
                supply_endpoint = endpoint
        if ssr_endpoint is None or supply_endpoint is None:
            raise RuntimeError(f"Could not identify both endpoints of wire {wire_index}")

        old_target = supply_endpoint.find("./connects/connect")
        old_part = instance_map[old_target.attrib["modelIndex"]]
        old_connector = old_target.attrib["connectorId"]
        remove_backlink(old_part, view_name, old_connector, wire_index)

        part_layer, _ = view_layer(view_name)
        old_target.attrib.update(modelIndex=NODEMCU_INDEX, connectorId="connector15", layer=part_layer)
        add_backlink(
            instance_map[NODEMCU_INDEX],
            view_name,
            "connector15",
            wire_index,
            supply_endpoint.attrib["connectorId"],
        )


def migrate_npn(instance_map: dict[str, ET.Element], npn_index: str, title: str) -> None:
    npn = instance_map[npn_index]
    if npn.attrib.get("moduleIdRef") == NPN_PART:
        return

    # Old power transistor: 0=B, 1=C, 2=E.  Selected TO-92: 1=B, 0=C, 2=E.
    for node in npn.findall(".//connector"):
        old = node.attrib.get("connectorId")
        if old == "connector0":
            node.attrib["connectorId"] = "connector1"
        elif old == "connector1":
            node.attrib["connectorId"] = "connector0"
    for part in instance_map.values():
        for link in part.findall(".//connect"):
            if link.attrib.get("modelIndex") != npn_index:
                continue
            old = link.attrib.get("connectorId")
            if old == "connector0":
                link.attrib["connectorId"] = "connector1"
            elif old == "connector1":
                link.attrib["connectorId"] = "connector0"

    npn.attrib.update(moduleIdRef=NPN_PART, path=NPN_PATH)
    npn.find("title").text = title


def retarget_wire_endpoint(
    instance_map: dict[str, ET.Element], wire_index: str, old_part_index: str,
    new_part_index: str, new_connector_id: str,
) -> None:
    """Move one end of a wire in every view and keep backlinks consistent."""
    wire = instance_map[wire_index]
    for view_name in ("breadboardView", "pcbView", "schematicView"):
        wire_view = wire.find(f"./views/{view_name}")
        if wire_view is None:
            continue
        moved_connector = None
        old_connector_id = None
        for endpoint in wire_view.findall("./connectors/connector"):
            target = endpoint.find("./connects/connect")
            if target is not None and target.attrib.get("modelIndex") == old_part_index:
                moved_connector = endpoint.attrib["connectorId"]
                old_connector_id = target.attrib["connectorId"]
                part_layer, _ = view_layer(view_name)
                target.attrib.update(
                    modelIndex=new_part_index,
                    connectorId=new_connector_id,
                    layer=part_layer,
                )
                break
        if moved_connector is None:
            # Idempotency: the endpoint may already have been moved.
            already_moved = any(
                endpoint.find("./connects/connect") is not None
                and endpoint.find("./connects/connect").attrib.get("modelIndex") == new_part_index
                and endpoint.find("./connects/connect").attrib.get("connectorId") == new_connector_id
                for endpoint in wire_view.findall("./connectors/connector")
            )
            if already_moved:
                continue
            raise RuntimeError(f"Wire {wire_index} has no endpoint at {old_part_index}")
        remove_backlink(instance_map[old_part_index], view_name, old_connector_id, wire_index)
        add_backlink(
            instance_map[new_part_index], view_name, new_connector_id,
            wire_index, moved_connector,
        )


def repair_driver_grounds(instance_map: dict[str, ET.Element]) -> None:
    # Earlier XML revisions accidentally moved the emitter/base pull-down net
    # to Vin while repurposing the old SSR input wire.  The emitter and 10 kΩ
    # must instead terminate at the NodeMCU GND net (connector13).
    for npn_index, wire_index in DRIVER_GROUND_WIRES.items():
        ssr_index = {
            "20003": "8601",
            "20013": "8604",
            "20023": "8606",
        }[npn_index]
        retarget_wire_endpoint(
            instance_map, wire_index, ssr_index, NODEMCU_INDEX, "connector13"
        )


def remove_unverified_pcb_routing(instance_map: dict[str, ET.Element]) -> None:
    """Remove inherited copper while preserving breadboard/schematic nets.

    A blank PCB route is safer than exportable but geometrically invalid copper.
    Fritzing can regenerate the ratsnest from the other synchronized views when
    the physical footprints have been checked and final routing begins.
    """
    for part in instance_map.values():
        pcb_view = part.find("./views/pcbView")
        if pcb_view is None:
            continue
        if part.attrib.get("moduleIdRef") == "WireModuleID":
            part.find("views").remove(pcb_view)
            continue
        connectors = pcb_view.find("connectors")
        if connectors is None:
            continue
        for node in connectors.findall("connector"):
            connects = node.find("connects")
            if connects is not None:
                connects.clear()


def validate_control_nets(root: ET.Element) -> None:
    instance_map = instances(root)
    graph: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for index, part in instance_map.items():
        view = part.find("./views/schematicView")
        if view is None:
            continue
        nodes = view.findall("./connectors/connector")
        if part.attrib.get("moduleIdRef") == "WireModuleID" and len(nodes) == 2:
            left = (index, nodes[0].attrib["connectorId"])
            right = (index, nodes[1].attrib["connectorId"])
            graph[left].add(right)
            graph[right].add(left)
        for node in nodes:
            source = (index, node.attrib["connectorId"])
            for link in node.findall("./connects/connect"):
                target = (link.attrib["modelIndex"], link.attrib["connectorId"])
                graph[source].add(target)
                graph[target].add(source)

    def connected(start: tuple[str, str], target: tuple[str, str]) -> bool:
        pending = [start]
        seen = {start}
        while pending:
            for neighbour in graph[pending.pop()]:
                if neighbour == target:
                    return True
                if neighbour not in seen:
                    seen.add(neighbour)
                    pending.append(neighbour)
        return start == target

    channels = (("8601", "20003"), ("8604", "20013"), ("8606", "20023"))
    for ssr_index, npn_index in channels:
        checks = {
            "J pin 0 to Vin/+5V": connected(
                (ssr_index, "connector0"), (NODEMCU_INDEX, "connector15")
            ),
            "J pin 1 to NPN collector": connected(
                (ssr_index, "connector1"), (npn_index, "connector0")
            ),
            "NPN emitter to GND": connected(
                (npn_index, "connector2"), (NODEMCU_INDEX, "connector13")
            ),
            "base isolated from Vin": not connected(
                (npn_index, "connector1"), (NODEMCU_INDEX, "connector15")
            ),
        }
        failed = [description for description, ok in checks.items() if not ok]
        if failed:
            raise RuntimeError(f"{SSR_CHANNELS[ssr_index]}: failed {', '.join(failed)}")

    peripheral_checks = {
        "DHT data D5": connected((NODEMCU_INDEX, "connector7"), ("7053", "connector2")),
        "OLED A SCL D1": connected((NODEMCU_INDEX, "connector1"), ("7240", "connector3")),
        "OLED A SDA D2": connected((NODEMCU_INDEX, "connector2"), ("7240", "connector2")),
        "OLED B SCL D1": connected((NODEMCU_INDEX, "connector1"), ("7243", "connector3")),
        "OLED B SDA D2": connected((NODEMCU_INDEX, "connector2"), ("7243", "connector2")),
        "RTC SCL D1": connected((NODEMCU_INDEX, "connector1"), ("7352", "connector8")),
        "RTC SDA D2": connected((NODEMCU_INDEX, "connector2"), ("7352", "connector9")),
        "control switch D0": connected((NODEMCU_INDEX, "connector0"), ("7733", "connector1")),
        "menu button D3": connected((NODEMCU_INDEX, "connector3"), ("8490", "connector1")),
        "select button D4": connected((NODEMCU_INDEX, "connector4"), ("8496", "connector1")),
        "potentiometer wiper A0": connected((NODEMCU_INDEX, "connector42"), ("8472", "connector1")),
        "Vin isolated from GND": not connected(
            (NODEMCU_INDEX, "connector15"), (NODEMCU_INDEX, "connector13")
        ),
    }
    failed = [description for description, ok in peripheral_checks.items() if not ok]
    if failed:
        raise RuntimeError(f"Peripheral net validation failed: {', '.join(failed)}")


def repair(root: ET.Element) -> None:
    instance_list = root.find("instances")
    instance_map = instances(root)

    boards = [
        part for part in instance_list.findall("instance")
        if part.attrib.get("moduleIdRef") == "TwoLayerRectanglePCBModuleID"
    ]
    if not boards:
        raise RuntimeError("No PCB found")
    board = boards[0]
    board.find("property[@name='width']").attrib["value"] = "120"
    board.find("property[@name='height']").attrib["value"] = "100"
    board.find("./views/pcbView/geometry").attrib.update(x="100", y="0")
    board.find("title").text = "PCB_CONTROL_SELV_ONLY"
    for duplicate in boards[1:]:
        instance_list.remove(duplicate)

    for ssr_index, title in SSR_CHANNELS.items():
        migrate_ssr(instance_map, ssr_index, title)
    for npn_index, title in NPN_CHANNELS.items():
        migrate_npn(instance_map, npn_index, title)
    repair_driver_grounds(instance_map)

    for part in instance_map.values():
        title = part.findtext("title", "")
        if title in TITLE_RENAMES:
            part.find("title").text = TITLE_RENAMES[title]
        position = PCB_POSITIONS.get(part.attrib["modelIndex"])
        geometry = part.find("./views/pcbView/geometry")
        if position and geometry is not None:
            geometry.attrib.update(x=str(position[0]), y=str(position[1]))

    remove_unverified_pcb_routing(instance_map)


def write_archive(source: Path, output: Path, xml_name: str, xml_bytes: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as repaired:
            for item in original.infolist():
                data = xml_bytes if item.filename == xml_name else original.read(item.filename)
                repaired.writestr(item, data)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", type=Path, default=Path("sketch_pcb.fzz"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.source

    with zipfile.ZipFile(args.source) as archive:
        xml_names = [name for name in archive.namelist() if name.endswith(".fz")]
        if len(xml_names) != 1:
            raise RuntimeError(f"Expected one .fz entry, found {xml_names}")
        xml_name = xml_names[0]
        root = ET.fromstring(archive.read(xml_name))

    repair(root)
    validate_control_nets(root)
    ET.indent(root, space="    ")
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    write_archive(args.source, output, xml_name, xml_bytes)
    print(f"Repaired {output}: one 120x100 mm SELV board, external SSR control connectors")


if __name__ == "__main__":
    main()
