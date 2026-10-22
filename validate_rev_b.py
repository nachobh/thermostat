#!/usr/bin/env python3
"""Independent geometric checks for the Rev B layout (SELV + 230 V).

Rules (all distances copper edge to copper edge, any layer combination for the
230 V / SELV pair, same layer otherwise):
  * SELV vs SELV, different nets:            >= 0.20 mm
  * 230 V vs 230 V, different nets:          >= 2.40 mm
  * 230 V vs SELV:                           >= 8.00 mm (reinforced)
  * copper to board edge:                    >= 0.50 mm (230 V: >= 2.0 mm)
  * every net is connected by real copper; SMD pads only on the top layer
  * component courtyards do not overlap; mounting-hole keepouts are free
This is a conservative check; the manufacturer's DFM still applies.
"""

from __future__ import annotations

import argparse
import importlib
import math
from collections import defaultdict

_parser = argparse.ArgumentParser()
_parser.add_argument("--design", default="build_rev_b_fzz", help="generator module (build_rev_b_fzz, build_rev_c_fzz)")
b = importlib.import_module(_parser.parse_args().design)

MM = b.S
VIA_RADIUS = 0.70 * MM


def seg_seg(a, c, d, e) -> float:
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    if (cross(a, c, d) * cross(a, c, e) < 0) and (cross(d, e, a) * cross(d, e, c) < 0):
        return 0.0
    return min(b.point_to_segment(a, d, e), b.point_to_segment(c, d, e),
               b.point_to_segment(d, a, c), b.point_to_segment(e, a, c))


class Copper:
    def __init__(self, kind, net, layers, geom, label, mains):
        self.kind, self.net, self.layers, self.geom, self.label, self.mains = kind, net, layers, geom, label, mains

    def distance(self, other: "Copper") -> float:
        """Edge-to-edge distance in px."""
        k1, k2 = self.kind, other.kind
        if k1 == "rect" or k2 == "rect":
            rect_obj, other_obj = (self, other) if k1 == "rect" else (other, self)
            r = rect_obj.geom
            if other_obj.kind == "rect":
                o = other_obj.geom
                dx = max(o[0] - r[2], r[0] - o[2], 0)
                dy = max(o[1] - r[3], r[1] - o[3], 0)
                return math.hypot(dx, dy)
            if other_obj.kind == "circle":
                (cx, cy), rad = other_obj.geom
                return b.segment_rect_distance((cx, cy), (cx, cy), r) - rad
            a, c, w = other_obj.geom
            return b.segment_rect_distance(a, c, r) - w / 2
        if k1 == "circle" and k2 == "circle":
            return math.dist(self.geom[0], other.geom[0]) - self.geom[1] - other.geom[1]
        if k1 == "seg" and k2 == "seg":
            return seg_seg(self.geom[0], self.geom[1], other.geom[0], other.geom[1]) - self.geom[2] / 2 - other.geom[2] / 2
        seg, circ = (self, other) if k1 == "seg" else (other, self)
        return b.point_to_segment(circ.geom[0], seg.geom[0], seg.geom[1]) - circ.geom[1] - seg.geom[2] / 2

    def bbox(self):
        if self.kind == "rect":
            return self.geom
        if self.kind == "circle":
            (x, y), r = self.geom
            return x - r, y - r, x + r, y + r
        a, c, w = self.geom
        return min(a[0], c[0]) - w / 2, min(a[1], c[1]) - w / 2, max(a[0], c[0]) + w / 2, max(a[1], c[1]) + w / 2


def main() -> None:
    points, segments, vias = b.route_everything()
    net_of = b.terminal_nets() if hasattr(b, "terminal_nets") else \
        {t: n for n, ts in {**b.NETS, **b.MAINS_NETS_TERMINALS}.items() for t in ts}
    nets_terminals = defaultdict(list)
    for table in (b.NETS, getattr(b, "MANUAL_NETS_TERMINALS", {}), b.MAINS_NETS_TERMINALS):
        for net, terminals in table.items():
            nets_terminals[net].extend(t for t in terminals if t not in nets_terminals[net])
    mains_parts = {"J20", "F2"}
    copper: list[Copper] = []
    for part in b.PARTS:
        for index, pad in enumerate(part.fp.pads):
            terminal = (part.ref, index)
            net = net_of.get(terminal, f"NC:{part.ref}:{pad.name.rstrip(chr(39))}")
            is_mains = net in b.MAINS_NETS or part.ref in mains_parts or (
                part.ref.startswith("RL") and not pad.name.startswith("A"))
            shape = b.PadShape(terminal)
            if pad.smd:
                copper.append(Copper("rect", net, shape.layers, shape.rect, f"{part.ref}.{pad.name}", is_mains))
            else:
                copper.append(Copper("circle", net, ("top", "bottom"), (shape.center, shape.radius),
                                     f"{part.ref}.{pad.name}", is_mains))
    for seg in segments:
        copper.append(Copper("seg", seg.net, (seg.layer,), (seg.start, seg.end, seg.width_mm * MM),
                             f"track {seg.net}", seg.net in b.MAINS_NETS))
    for via in vias:
        copper.append(Copper("circle", via.net, ("top", "bottom"), (via.point, VIA_RADIUS), f"via {via.net}", False))

    failures = []
    nearest = defaultdict(lambda: float("inf"))
    boxes = [c.bbox() for c in copper]
    reach = 14.0 * MM
    for i, first in enumerate(copper):
        bx = boxes[i]
        for j in range(i + 1, len(copper)):
            other = copper[j]
            if first.net == other.net:
                continue
            ob = boxes[j]
            if ob[0] > bx[2] + reach or bx[0] > ob[2] + reach or ob[1] > bx[3] + reach or bx[1] > ob[3] + reach:
                continue
            if first.mains != other.mains:
                rule, required = "230V-SELV", b.MAINS_SELV_MM
            elif first.mains:
                if not set(first.layers) & set(other.layers):
                    continue
                rule, required = "230V-230V", b.MAINS_MAINS_MM
            else:
                if not set(first.layers) & set(other.layers):
                    continue
                rule, required = "SELV-SELV", 0.20
            gap = first.distance(other) / MM
            nearest[rule] = min(nearest[rule], gap)
            if gap < required - 1e-6:
                failures.append((rule, gap, first.label, other.label, first.net, other.net))

    # Connectivity through copper only.
    parent = {}

    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def join(x, y):
        parent[find(x)] = find(y)

    def key(net, layer, p):
        return net, layer, round(p[0], 3), round(p[1], 3)

    for seg in segments:
        join(key(seg.net, seg.layer, seg.start), key(seg.net, seg.layer, seg.end))
    for via in vias:
        join(key(via.net, "top", via.point), key(via.net, "bottom", via.point))
    for net, terminals in nets_terminals.items():
        for t in terminals:
            layers = b.terminal_layers(t)
            if len(layers) == 2:
                join(key(net, "top", points[t]), key(net, "bottom", points[t]))
        first = find(key(net, b.terminal_layers(terminals[0])[0], points[terminals[0]]))
        for t in terminals[1:]:
            if find(key(net, b.terminal_layers(t)[0], points[t])) != first:
                failures.append(("unrouted", -1, net, str(t), "", ""))
    for seg in segments:
        for t in (seg.start_terminal, seg.end_terminal):
            if t is not None and seg.layer not in b.terminal_layers(t):
                failures.append(("smd-bottom", -1, seg.net, str(t), "", ""))

    # Board edge.
    x0, y0 = b.BOARD_X, b.BOARD_Y
    x1, y1 = x0 + b.BOARD_W, y0 + b.BOARD_H
    for c, box in zip(copper, boxes):
        margin = min(box[0] - x0, box[1] - y0, x1 - box[2], y1 - box[3]) / MM
        need = 2.0 if c.mains else 0.5
        nearest["edge"] = min(nearest["edge"], margin)
        if margin < need:
            failures.append(("edge", margin, c.label, "", c.net, ""))

    # Courtyards and mounting holes.
    bodies = []
    bottom_bodies = []
    for part in b.PARTS:
        for bx0, by0, bx1, by1 in part.fp.bodies:
            box = (part.ref, part.x + bx0, part.y + by0, part.x + bx1, part.y + by1)
            (bottom_bodies if getattr(part.fp, "bottom", False) else bodies).append(box)
    # A part on the bottom side must not sit on through-hole solder joints.
    for ref, x0b, y0b, x1b, y1b in bottom_bodies:
        for part in b.PARTS:
            for pad in part.fp.pads:
                if pad.smd:
                    continue
                cx, cy, r = part.x + pad.x, part.y + pad.y, pad.dia / 2 + 0.5
                d = math.hypot(max(x0b - cx, 0, cx - x1b), max(y0b - cy, 0, cy - y1b))
                nearest["bottom-body-THT"] = min(nearest["bottom-body-THT"], d - r)
                if d < r:
                    failures.append(("bottom-body-THT", d - r, ref, f"{part.ref}.{pad.name}", "", ""))
    for i, first in enumerate(bodies):
        if min(first[1], first[2], b.BOARD_W_MM - first[3], b.BOARD_H_MM - first[4]) < 0.5:
            failures.append(("body-edge", -1, first[0], "", "", ""))
        for other in bodies[i + 1:]:
            if first[0] == other[0]:
                continue
            ox = min(first[3], other[3]) - max(first[1], other[1])
            oy = min(first[4], other[4]) - max(first[2], other[2])
            if ox > 0 and oy > 0:
                failures.append(("body-overlap", -1, first[0], other[0], f"{ox:.2f}", f"{oy:.2f}"))
    mount_gap = float("inf")
    for mx, my in b.MOUNT_CENTERS_MM:
        for ref, bx0, by0, bx1, by1 in bodies + [("U1 module", *b.NODE_MODULE_MM)]:
            if ref == "U1":
                continue      # socket strips: covered by the module outline below
            d = math.hypot(max(bx0 - mx, 0, mx - bx1), max(by0 - my, 0, my - by1)) - b.MOUNT_KEEPOUT_MM
            mount_gap = min(mount_gap, d)
            if d < 0:
                failures.append(("mount-body", d, ref, f"H@{mx},{my}", "", ""))
        centre = b.px(mx, my)
        for c in copper:
            hole = Copper("circle", "MOUNT", ("top", "bottom"), (centre, b.MOUNT_KEEPOUT_MM * MM), "mount", False)
            d = c.distance(hole) / MM
            need = 4.0 if c.mains else 0.2
            mount_gap = min(mount_gap, d)
            if d < need:
                failures.append(("mount-copper", d, c.label, f"H@{mx},{my}", c.net, ""))

    print(f"{len(b.PARTS)} parts, {sum(len(p.fp.pads) for p in b.PARTS)} pads, {len(segments)} tracks, {len(vias)} vias")
    print("Minimum gaps (mm):", {k: round(v, 3) for k, v in sorted(nearest.items())})
    print(f"Minimum mounting-hole keepout margin: {mount_gap:.3f} mm")
    for failure in sorted(failures, key=lambda f: f[1])[:60]:
        print(failure[0], f"{failure[1]:.3f} mm" if failure[1] >= 0 else "", *failure[2:])
    print(f"FAILURES: {len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
