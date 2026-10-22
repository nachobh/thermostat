#!/usr/bin/env python3
"""Independent geometric checks for the generated SELV Fritzing layout.

Coordinates come from the actual Fritzing part SVGs, not the routing grid.
This is a conservative copper DRC; the manufacturer should still run its DFM.
"""

from __future__ import annotations

import math
from xml.etree import ElementTree as ET

import build_universal_fzz as board

MM = board.DPI / 25.4
TRACK_RADIUS = board.TRACE_MILS * board.DPI / 2000
CLEARANCE = 0.20 * MM
VIA_RADIUS = 0.70 * MM


def pad_radius(part: board.Part, connector_id: str) -> float:
    if part.kind in ("jstxh3", "jstxh4", "jstxh5"):
        return 0.90 * MM
    if part.kind == "terminal2":
        return 1.00 * MM
    if part.kind == "bc547":
        return 0.90 * MM
    kind = board.KINDS[part.kind]
    fzp = ET.parse(board.CORE / kind.fzp).getroot()
    image = fzp.find("./views/pcbView/layers").attrib["image"]
    svg = ET.parse(board.svg_path(image)).getroot()
    width = board.length_px(svg.attrib["width"])
    viewbox = [float(x) for x in svg.attrib.get("viewBox", f"0 0 {width} {board.length_px(svg.attrib['height'])}").replace(",", " ").split()]
    factor = width / viewbox[2]
    connector = fzp.find(f"./connectors/connector[@id='{connector_id}']")
    svg_id = connector.find("./views/pcbView/p").attrib["svgId"]
    elements = [node for node in svg.iter() if node.attrib.get("id") == svg_id]
    element = elements[0]
    radius = float(element.attrib.get("r", "0")) + float(element.attrib.get("stroke-width", "0")) / 2
    if element.tag.endswith("rect"):
        radius = max(float(element.attrib["width"]), float(element.attrib["height"])) / 2
    return radius * factor


def point_segment_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    norm = dx * dx + dy * dy
    if norm == 0:
        return math.dist(point, start)
    fraction = max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / norm))
    return math.dist(point, (start[0] + fraction * dx, start[1] + fraction * dy))


def segment_distance(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def in_box(p, q, r):
        return min(p[0], q[0]) - 1e-8 <= r[0] <= max(p[0], q[0]) + 1e-8 and min(p[1], q[1]) - 1e-8 <= r[1] <= max(p[1], q[1]) + 1e-8

    crosses = ((cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0)
               or any(abs(cross(x, y, p)) < 1e-8 and in_box(x, y, p)
                      for x, y, p in ((a, b, c), (a, b, d), (c, d, a), (c, d, b))))
    if crosses:
        return 0.0
    return min(point_segment_distance(a, c, d), point_segment_distance(b, c, d),
               point_segment_distance(c, a, b), point_segment_distance(d, a, b))


def main() -> None:
    points = board.part_points()
    segments, via_list = board.route_all(points)
    vias = list(dict.fromkeys(via_list))
    terminal_net = {terminal: net for net, (_, terminals) in board.NETS.items() for terminal in terminals}
    part_map = {part.ref: part for part in board.PARTS}
    pads = [(terminal, point, terminal_net[terminal], pad_radius(part_map[terminal[0]], terminal[1]))
            for terminal, point in points.items() if terminal in terminal_net]
    failures = []
    nearest = {"track-track": float("inf"), "track-pad": float("inf"),
               "pad-pad": float("inf"), "via-track": float("inf"),
               "via-pad": float("inf"), "via-via": float("inf")}

    for index, first in enumerate(segments):
        for other in segments[index + 1:]:
            if first.layer != other.layer or first.net == other.net:
                continue
            gap = segment_distance(first.start, first.end, other.start, other.end) - 2 * TRACK_RADIUS
            nearest["track-track"] = min(nearest["track-track"], gap)
            if gap < CLEARANCE - 1e-6:
                failures.append(("track-track", gap, first.net, other.net, first.start, other.start))
        for terminal, point, net, radius in pads:
            if net == first.net:
                continue
            gap = point_segment_distance(point, first.start, first.end) - radius - TRACK_RADIUS
            nearest["track-pad"] = min(nearest["track-pad"], gap)
            if gap < CLEARANCE - 1e-6:
                failures.append(("track-pad", gap, first.net, net, first.start, terminal))

    for index, (terminal, point, net, radius) in enumerate(pads):
        for other_terminal, other_point, other_net, other_radius in pads[index + 1:]:
            if net == other_net:
                continue
            gap = math.dist(point, other_point) - radius - other_radius
            nearest["pad-pad"] = min(nearest["pad-pad"], gap)
            if gap < CLEARANCE - 1e-6:
                failures.append(("pad-pad", gap, net, other_net, terminal, other_terminal))

    for via in vias:
        for segment in segments:
            if via.net == segment.net:
                continue
            gap = point_segment_distance(via.point, segment.start, segment.end) - VIA_RADIUS - TRACK_RADIUS
            nearest["via-track"] = min(nearest["via-track"], gap)
            if gap < CLEARANCE - 1e-6:
                failures.append(("via-track", gap, via.net, segment.net, via.point, segment.start))
        for terminal, point, net, radius in pads:
            if net == via.net:
                continue
            gap = math.dist(via.point, point) - VIA_RADIUS - radius
            nearest["via-pad"] = min(nearest["via-pad"], gap)
            if gap < CLEARANCE - 1e-6:
                failures.append(("via-pad", gap, via.net, net, via.point, terminal))

    for index, via in enumerate(vias):
        for other in vias[index + 1:]:
            if via.net == other.net:
                continue
            gap = math.dist(via.point, other.point) - 2 * VIA_RADIUS
            nearest["via-via"] = min(nearest["via-via"], gap)
            if gap < CLEARANCE - 1e-6:
                failures.append(("via-via", gap, via.net, other.net, via.point, other.point))

    # Independently check that every named terminal is joined by actual copper
    # and plated transitions, rather than trusting Fritzing's logical netlist.
    parent = {}

    def root(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def join(a, b):
        parent[root(a)] = root(b)

    def node(layer, point):
        return layer, round(point[0], 4), round(point[1], 4)

    for segment in segments:
        join((segment.net, *node(segment.layer, segment.start)),
             (segment.net, *node(segment.layer, segment.end)))
    for via in vias:
        join((via.net, *node("top", via.point)), (via.net, *node("bottom", via.point)))
    for net, (_, terminals) in board.NETS.items():
        for terminal in terminals:
            point = points[terminal]
            join((net, *node("top", point)), (net, *node("bottom", point)))
        first = root((net, *node("top", points[terminals[0]])))
        for terminal in terminals[1:]:
            if root((net, *node("top", points[terminal]))) != first:
                failures.append(("unrouted", -1, net, terminal))

    board_box = (board.BOARD_X, board.BOARD_Y,
                 board.BOARD_X + board.BOARD_W, board.BOARD_Y + board.BOARD_H)
    edge_margin = 1.0 * MM
    for segment in segments:
        for point in (segment.start, segment.end):
            if min(point[0] - board_box[0], point[1] - board_box[1],
                   board_box[2] - point[0], board_box[3] - point[1]) < edge_margin + TRACK_RADIUS:
                failures.append(("track-edge", -1, segment.net, point))
    for terminal, point, net, radius in pads:
        if min(point[0] - board_box[0], point[1] - board_box[1],
               board_box[2] - point[0], board_box[3] - point[1]) < edge_margin + radius:
            failures.append(("pad-edge", -1, net, terminal))

    bodies = []
    for part in board.PARTS:
        if part.kind in ("jstxh3", "jstxh4", "jstxh5"):
            width, height = 4.9 + 2.5 * (part.connectors - 1), 5.75
        elif part.kind == "terminal2":
            width, height = 10.16, 9.8
        elif part.kind == "bc547":
            width, height = 7.28, 5.2
        else:
            fzp = ET.parse(board.CORE / board.KINDS[part.kind].fzp).getroot()
            image = fzp.find("./views/pcbView/layers").attrib["image"]
            svg = ET.parse(board.svg_path(image)).getroot()
            width = board.length_px(svg.attrib["width"]) / MM
            height = board.length_px(svg.attrib["height"]) / MM
        x0, y0 = part.x, part.y
        x1, y1 = x0 + width * MM, y0 + height * MM
        bodies.append((part.ref, x0, y0, x1, y1))
        if min(x0 - board_box[0], y0 - board_box[1],
               board_box[2] - x1, board_box[3] - y1) < 2 * MM:
            failures.append(("body-edge", -1, part.ref, (x0, y0, x1, y1)))
    for index, first in enumerate(bodies):
        for other in bodies[index + 1:]:
            overlap_x = min(first[3], other[3]) - max(first[1], other[1])
            overlap_y = min(first[4], other[4]) - max(first[2], other[2])
            if overlap_x > 0 and overlap_y > 0:
                failures.append(("body-overlap", -1, first[0], other[0],
                                 round(overlap_x / MM, 3), round(overlap_y / MM, 3)))

    mount_radius = board.MOUNT_KEEPOUT_MM * MM
    mount_gap = float("inf")
    for number, (x_mm, y_mm) in enumerate(board.MOUNT_CENTERS_MM, start=1):
        center = board.mount_center_px(x_mm, y_mm)
        if min(center[0] - board_box[0], center[1] - board_box[1],
               board_box[2] - center[0], board_box[3] - center[1]) < mount_radius:
            failures.append(("mount-edge", -1, f"H{number}", center))
        for ref, x0, y0, x1, y1 in bodies:
            distance = math.dist(center, (max(x0, min(center[0], x1)), max(y0, min(center[1], y1))))
            mount_gap = min(mount_gap, distance - mount_radius)
            if distance < mount_radius:
                failures.append(("mount-body", distance - mount_radius, f"H{number}", ref))
        for terminal, point, net, radius in pads:
            gap = math.dist(center, point) - mount_radius - radius
            mount_gap = min(mount_gap, gap)
            if gap < CLEARANCE:
                failures.append(("mount-pad", gap, f"H{number}", terminal))
        for via in vias:
            gap = math.dist(center, via.point) - mount_radius - VIA_RADIUS
            mount_gap = min(mount_gap, gap)
            if gap < CLEARANCE:
                failures.append(("mount-via", gap, f"H{number}", via.net))
        for segment in segments:
            gap = point_segment_distance(center, segment.start, segment.end) - mount_radius - TRACK_RADIUS
            mount_gap = min(mount_gap, gap)
            if gap < CLEARANCE:
                failures.append(("mount-track", gap, f"H{number}", segment.net))

    print(f"{len(board.PARTS)} parts, {len(pads)} pads, {len(segments)} tracks, {len(vias)} vias")
    print(f"Mounting holes: {len(board.MOUNT_CENTERS_MM)} x Ø{board.MOUNT_DRILL_MM:.1f} mm; minimum keepout gap: {mount_gap / MM:.3f} mm")
    print("Minimum clearances (mm):", {key: round(value / MM, 3) for key, value in nearest.items()})
    print(f"Required copper clearance: {CLEARANCE / MM:.2f} mm")
    for failure in sorted(failures, key=lambda item: item[1])[:50]:
        print(failure[0], f"{failure[1] / MM:.3f} mm", *failure[2:])
    print(f"FAILURES: {len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
