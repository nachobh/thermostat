#!/usr/bin/env python3
"""STL de la caja v8 (preliminar, sin tapa frontal): carcasa, cubierta de 230 V (bandeja + tabique) y tapa de la cubierta.

Cotas de build_carcasa_v8.py. Salida en carcasa/stl_v8/. Pantalla, NodeMCU, DHT y mini-placa son
medidas SUPUESTAS; la pantalla se pega sobre la pestaña superior de las paredes (cinta VHB o similar).
"""
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_carcasa_v8 as B  # noqa: E402
from build_stl_v4 import box, cyl, union, diff, inter  # noqa: E402

Q, V = B.Q, B.VENTS
OUT = HERE / "stl_v8"
OUT.mkdir(exist_ok=True)
EPS = 0.2
OW, OH, IX, IY = Q["outer_w"] / 2, Q["outer_h"] / 2, Q["inner_w"] / 2, Q["inner_h"] / 2
FL, ZT, WL = Q["floor"], Q["wall_top"], Q["wall"]
DX0, DX1 = Q["deck_x0"], Q["part_x0"] + Q["part_t"]


def sbox(x0, x1, y0, y1, z0, z1):
    return box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z1)


def cyl_x(r, x0, x1, y, z, sections=48):
    m = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=sections)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
    m.apply_translation(((x0 + x1) / 2, y, z))
    return m


def build_shell():
    body = diff(box(-OW, OW, -OH, OH, 0, ZT), [box(-IX, IX, -IY, IY, FL, ZT + EPS)])
    cut = [box(a, b, IY - EPS, OH + EPS, c, d) for a, b, c, d in V["top"]]
    cut.append(box(Q["node_x"] - 6, Q["node_x"] + 6, -OH - EPS, -IY + EPS, 3.2, 12.2))             # USB hacia abajo
    cut += [box(IX - EPS, OW + EPS, c, d, a, b) for a, b, c, d in V["right_dht"]]                   # hueco del DHT22
    cut += [cyl_x(6.0, -OW - EPS, -IX + EPS, y, 38.0) for y in (20.0, 40.0)]                        # entradas de cable Ø12 (pared izq.)
    cut += [cyl(2.25, -EPS, FL + EPS, x=0.0, y=sy * 63.0) for sy in (-1, 1)]
    shell = diff(body, cut)
    add = []
    cx = Q["pcb_cx"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * 45.0, sy * 45.0
            add.append(diff(cyl(3.5, FL - 0.1, Q["pcb_z"], x=x, y=y), [cyl(1.3, FL + 0.5, Q["pcb_z"] + EPS, x=x, y=y)]))
    fz = ZT - Q["flange_t"]                                                                          # pestaña de pegado, 4 mm hacia dentro
    add.append(sbox(-IX - 0.1, IX + 0.1, IY - Q["flange_w"], IY + 0.1, fz, ZT))
    add.append(sbox(-IX - 0.1, IX + 0.1, -IY + Q["flange_w"], -IY - 0.1, fz, ZT))
    add.append(sbox(-IX - 0.1, -IX + Q["flange_w"], -IY, IY, fz, ZT))
    add.append(sbox(IX + 0.1, IX - Q["flange_w"], -IY, IY, fz, ZT))
    for sy in (-1, 1):                                                                               # orejas de pared
        y0, y1 = (OH - 0.1, OH + 13.0) if sy > 0 else (-OH - 13.0, -OH + 0.1)
        add.append(diff(box(-8, 8, y0, y1, 0, FL), [cyl(2.25, -EPS, FL + EPS, x=0.0, y=sy * 63.0)]))
    # repisas de la cubierta de 230 V y de su tapa (izquierda, arriba y abajo)
    for z0, z1 in ((Q["deck_z0"] - 3.5, Q["deck_z0"]), (Q["cover_z0"] - 3.5, Q["cover_z0"])):
        add.append(sbox(-IX - 0.1, -IX + 2.7, -IY, IY, z0, z1))
        add.append(sbox(DX0, Q["part_x0"], IY + 0.1, IY - 2.7, z0, z1))
        add.append(sbox(DX0, Q["part_x0"], -IY - 0.1, -IY + 2.7, z0, z1))
    for y in (-IY + 2.7, 10.75, IY - 2.7):                                                           # costillas bajo el borde derecho de la cubierta
        add.append(sbox(Q["part_x0"], Q["part_x0"] + 1.6, y - 1.5, y + 1.5, FL - 0.1, Q["deck_z0"]))
    nx, ny = Q["node_x"], Q["node_y"]
    for dx in (-12.5, 12.5):
        for dy in (-26.0, 26.0):
            add.append(sbox(nx + dx - 3, nx + dx + 3, ny + dy - 3, ny + dy + 3, FL - 0.1, FL + Q["node_pad"]))      # apoyos del NodeMCU
    for sx in (-1, 1):                                                                               # esquineros del NodeMCU
        for sy in (-1, 1):
            cxp, cyp = nx + sx * (Q["node_w"] / 2 + 0.2), ny + sy * (Q["node_l"] / 2 + 0.2)
            zt_ = Q["node_zb"] + 3.0
            add.append(sbox(cxp, cxp - sx * 8, cyp, cyp + sy * 1.2, FL - 0.1, zt_))
            add.append(sbox(cxp, cxp + sx * 1.2, cyp, cyp - sy * 8, FL - 0.1, zt_))
    dx_, dy_ = Q["dht_x"], Q["dht_y"]                                                                # DHT22: retén en U abierto hacia +x
    hw, hl = Q["dht_w"] / 2, Q["dht_l"] / 2
    add.append(sbox(dx_ - hw - 1.4, dx_ - hw - 0.2, dy_ - hl - 1.4, dy_ + hl + 1.4, FL - 0.1, FL + 6))
    add.append(sbox(dx_ - hw - 1.4, dx_ + hw, dy_ + hl + 0.2, dy_ + hl + 1.4, FL - 0.1, FL + 6))
    add.append(sbox(dx_ - hw - 1.4, dx_ + hw, dy_ - hl - 0.2, dy_ - hl - 1.4, FL - 0.1, FL + 6))
    add.append(sbox(Q["part_x0"] + Q["part_t"], IX + 0.1, Q["baf_y"] - 0.75, Q["baf_y"] + 0.75, FL - 0.1, Q["deck_z0"]))   # deflector térmico
    return union([shell] + add)


def build_deck():
    z0, z1 = Q["deck_z0"], Q["deck_z1"]
    sl = Q["slot"]
    plate = sbox(DX0, DX1, -IY + 0.2, IY - 0.2, z0, z1)
    plate = diff(plate, [box(sl[0], sl[1], sl[2], sl[3], z0 - EPS, z1 + EPS)])
    part = sbox(Q["part_x0"], Q["part_x0"] + Q["part_t"], -IY + 0.2, IY - 0.2, z0, Q["cover_z0"])
    add = [plate, part]
    for x, y in Q["mb_posts"]:
        add.append(diff(cyl(2.5, z1 - 0.1, Q["mb_z0"], x=x, y=y), [cyl(1.1, Q["mb_z0"] - 4, Q["mb_z0"] + EPS, x=x, y=y)]))
    return union(add)


def build_cover():
    return sbox(DX0, DX1, -IY + 0.2, IY - 0.2, Q["cover_z0"], Q["cover_z1"])


def export(name, m, shift=(0, 0, 0)):
    m = m.copy()
    m.apply_translation(shift)
    m.export(OUT / name)


if __name__ == "__main__":
    shell, deck, cover = build_shell(), build_deck(), build_cover()
    names = (("carcasa", shell), ("cubierta", deck), ("tapa_cubierta", cover))
    for n, m in names:
        print(n, "estanca" if m.is_watertight else "NO ESTANCA", round(m.volume / 1000, 1), "cm3", np.round(m.extents, 1).tolist())
    export("carcasa.stl", shell)
    export("cubierta.stl", deck, shift=(0, 0, -Q["deck_z0"]))
    export("tapa_cubierta.stl", cover, shift=(0, 0, -Q["cover_z0"]))
    trimesh.util.concatenate([shell, deck, cover]).export(OUT / "ensamblado.stl")
    nx, ny, cx = Q["node_x"], Q["node_y"], Q["pcb_cx"]
    env = {
        "PCB (placa)": box(cx - 50, cx + 50, -50, 50, Q["pcb_z"], Q["pcb_top"]),
        "PCB (componentes)": box(cx - 47.5, cx + 47.5, -46.8, 46.8, Q["pcb_top"], Q["zone_top"]),
        "NodeMCU (placa+conectores)": box(nx - 15.5, nx + 15.5, ny - 29, ny + 29, Q["node_zb"], Q["node_zt"]),
        "NodeMCU (ESP-12 y USB)": trimesh.util.concatenate([box(nx - 6, nx + 6, ny - 2, ny + 14, Q["node_zb"] - 3.0, Q["node_zb"]),
                                                            box(nx - 3, nx + 3, ny - 29, ny - 21, Q["node_zb"] - 2.8, Q["node_zb"])]),
        "DHT22": box(Q["dht_x"] - Q["dht_w"] / 2, Q["dht_x"] + Q["dht_w"] / 2, Q["dht_y"] - Q["dht_l"] / 2, Q["dht_y"] + Q["dht_l"] / 2, FL, FL + 1.6 + Q["dht_t"]),
        "pantalla": box(-Q["disp_w"] / 2, Q["disp_w"] / 2, -Q["disp_h"] / 2, Q["disp_h"] / 2, Q["disp_z0"], Q["depth"]),
        "mini-placa": box(Q["mb_x0"], Q["mb_x1"], Q["mb_y0"], Q["mb_y1"], Q["mb_z0"], Q["rel_z0"]),
        "relés": trimesh.util.concatenate([box(xs - Q["rel_w"] / 2, xs + Q["rel_w"] / 2, Q["rel_y"] - Q["rel_l"] / 2 - 3.0, Q["rel_y"] + Q["rel_l"] / 2,
                                                Q["rel_z0"], Q["rel_z1"]) for xs in Q["rel_x"]]),
        "bornas": box(Q["strip_x"] - 10.2, Q["strip_x"] + 10.2, Q["strip_y"] - Q["strip_w"] / 2, Q["strip_y"] + Q["strip_w"] / 2, Q["rel_z0"], Q["rel_z0"] + Q["strip_h"]),
    }
    bad = 0
    for pn, pm in env.items():
        row = []
        for n, m in names:
            try:
                v = inter(m, pm).volume
            except Exception:
                v = 0.0
            bad += v > 1
            row.append(f"{n}={v:.0f}")
        print(f"interferencia {pn}: " + "  ".join(row))
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = inter(names[i][1], names[j][1]).volume
            bad += v > 1
            print(f"interferencia {names[i][0]}/{names[j][0]}: {v:.0f} mm3")
    print("INTERFERENCIAS >1 mm3:", int(bad))
