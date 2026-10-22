#!/usr/bin/env python3
"""STL de la caja v7 (preliminar): carcasa, tapa y cubierta de la bolsa de 230 V.

Cotas de build_carcasa_v7.py. Salida en carcasa/stl_v7/. Pantalla, NodeMCU, DHT y mini-placa
son medidas SUPUESTAS; repasar con las piezas reales (y el plano mecánico de DWIN).
"""
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_carcasa_v7 as B  # noqa: E402
from build_stl_v4 import box, cyl, union, diff, inter  # noqa: E402

Q, V = B.Q, B.VENTS
OUT = HERE / "stl_v7"
OUT.mkdir(exist_ok=True)
EPS = 0.2
OW, OH, IX, IY = Q["outer_w"] / 2, Q["outer_h"] / 2, Q["inner_w"] / 2, Q["inner_h"] / 2
ZL, ZD, W = Q["lid_in"], Q["depth"], Q["wall"]
COL = [(sx * Q["col"][0], sy * Q["col"][1]) for sx in (-1, 1) for sy in (-1, 1)]


def sbox(x0, x1, y0, y1, z0, z1):
    return box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z1)


def cyl_x(r, x0, x1, y, z, sections=48):
    m = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=sections)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
    m.apply_translation(((x0 + x1) / 2, y, z))
    return m


def build_shell():
    body = diff(box(-OW, OW, -OH, OH, 0, ZL), [box(-IX, IX, -IY, IY, W, ZL + EPS)])
    cut = [box(a, b, IY - EPS, OH + EPS, c, d) for a, b, c, d in V["top"]]
    cut += [box(a, b, -OH - EPS, -IY + EPS, c, d) for a, b, c, d in V["bottom_dht"]]
    cut.append(box(Q["node_x"] - 6, Q["node_x"] + 6, -OH - EPS, -IY + EPS, 3.2, 12.2))           # USB hacia abajo
    cut += [cyl_x(6.0, IX - EPS, OW + EPS, y, 15.0) for y in (15.0, 38.0)]                          # entradas de cable Ø12
    cut += [cyl(2.25, -EPS, W + EPS, x=0.0, y=sy * 67.0) for sy in (-1, 1)]
    shell = diff(body, cut)
    add = []
    cx = Q["pcb_cx"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * 45.0, sy * 45.0
            add.append(diff(cyl(3.5, W - 0.1, Q["pcb_z"], x=x, y=y), [cyl(1.3, W + 0.5, Q["pcb_z"] + EPS, x=x, y=y)]))
    for x, y in COL:                                                                              # columnas de la tapa
        add.append(diff(cyl(Q["col_r"], W - 0.1, ZL, x=x, y=y), [cyl(1.0, ZL - 14, ZL + EPS, x=x, y=y)]))
    for sy in (-1, 1):                                                                            # orejas de pared (arriba y abajo)
        y0, y1 = (OH - 0.1, 74.0) if sy > 0 else (-74.0, -OH + 0.1)
        add.append(diff(box(-8, 8, y0, y1, 0, W), [cyl(2.25, -EPS, W + EPS, x=0.0, y=sy * 67.0)]))
    zc = Q["cover_z0"]
    add.append(sbox(Q["part_x0"], Q["part_x0"] + Q["part_t"], Q["part_y0"], IY + 0.1, W - 0.1, zc))                       # tabique vertical
    add.append(sbox(Q["part_x0"], IX + 0.1, Q["part_y0"], Q["part_y0"] + Q["part_t"], W - 0.1, zc))                       # tabique horizontal
    add.append(sbox(Q["part_x0"] + Q["part_t"], IX + 0.1, IY - 3.0, IY + 0.1, zc - 3.5, zc))                              # repisas de la cubierta
    add.append(sbox(IX - 3.0, IX + 0.1, Q["part_y0"] + Q["part_t"], IY - 3.0, zc - 3.5, zc))
    for x, y in Q["mb_posts"]:                                                                      # postes de la mini-placa
        add.append(diff(cyl(2.5, W - 0.1, Q["mb_z0"], x=x, y=y), [cyl(1.1, Q["mb_z0"] - 4, Q["mb_z0"] + EPS, x=x, y=y)]))
    nx, ny = Q["node_x"], Q["node_y"]
    for dx in (-12.5, 12.5):
        for dy in (-26.0, 26.0):
            add.append(sbox(nx + dx - 3, nx + dx + 3, ny + dy - 3, ny + dy + 3, W - 0.1, W + Q["node_pad"]))               # apoyos del NodeMCU
    for sx in (-1, 1):                                                                            # esquineros del NodeMCU
        for sy in (-1, 1):
            cxp, cyp = nx + sx * (Q["node_w"] / 2 + 0.2), ny + sy * (Q["node_l"] / 2 + 0.2)
            zt_ = Q["node_zb"] + 3.0
            add.append(sbox(cxp, cxp + sx * 1.2, cyp, cyp - sy * 8, W - 0.1, zt_))
            add.append(sbox(cxp, cxp - sx * 8, cyp, cyp + sy * 1.2, W - 0.1, zt_))
    dx_, dy_ = Q["dht_x"], Q["dht_y"]                                                             # DHT22: retén en L (+y, +x)
    hw, hl = Q["dht_w"] / 2, Q["dht_l"] / 2
    add.append(sbox(dx_ - hw - 1.2, dx_ + hw + 1.4, dy_ + hl + 0.2, dy_ + hl + 1.4, W - 0.1, W + 6))
    add.append(sbox(dx_ + hw + 0.2, dx_ + hw + 1.4, dy_ - hl - 1.2, dy_ + hl + 1.4, W - 0.1, W + 6))
    add.append(sbox(Q["baf_x"] - 0.75, Q["baf_x"] + 0.75, -IY + 0.5, -22.0, W - 0.1, 25.0))                                 # deflector térmico
    return union([shell] + add)


def build_lid():
    plate = box(-OW, OW, -OH, OH, ZL, ZD)
    ww, wh = Q["act_w"] + 2 * Q["win_pad"], Q["act_h"] + 2 * Q["win_pad"]
    cut = [box(-ww / 2, ww / 2, -wh / 2, wh / 2, ZL - EPS, ZD + EPS)]
    for x, y in COL:
        cut += [cyl(1.7, ZL - EPS, ZD + EPS, x=x, y=y), cyl(3.2, ZD - 1.5, ZD + EPS, x=x, y=y)]
    lid = diff(plate, cut)
    dw, dh = Q["disp_w"] + 0.4, Q["disp_h"] + 0.4
    rim = diff(box(-dw / 2 - 1.2, dw / 2 + 1.2, -dh / 2 - 1.2, dh / 2 + 1.2, ZL - 3.0, ZL + 0.1),
               [box(-dw / 2, dw / 2, -dh / 2, dh / 2, ZL - 3.2, ZL + 0.2)])
    rim = diff(rim, [box(-5, 5, -dh / 2 - 1.4, -dh / 2 + 0.1, ZL - 3.2, ZL + 0.2),
                     box(dw / 2 - 0.1, dw / 2 + 1.4, -5, 5, ZL - 3.2, ZL + 0.2)])
    lid = union([lid, rim])
    lid = diff(lid, [cyl(Q["col_r"] + 0.4, ZL - 6, ZL, x=x, y=y) for x, y in COL])
    return inter(lid, box(-OW, OW, -OH, OH, ZL - 6, ZD + 1))


def build_cover():
    z0, z1 = Q["cover_z0"], Q["cover_z1"]
    plate = box(Q["part_x0"] + Q["part_t"] + 0.2, IX - 0.2, Q["part_y0"] + Q["part_t"] + 0.2, IY - 0.2, z0, z1)
    return diff(plate, [cyl(3.2, z0 - EPS, z1 + EPS, x=Q["col"][0], y=Q["col"][1])])


def export(name, m, shift=(0, 0, 0), flip_z=False):
    m = m.copy()
    if flip_z:
        m.apply_transform(np.diag([1, 1, -1, 1]))
        m.invert()
    m.apply_translation(shift)
    m.export(OUT / name)


if __name__ == "__main__":
    shell, lid, cover = build_shell(), build_lid(), build_cover()
    names = (("carcasa", shell), ("tapa", lid), ("cubierta_bolsa", cover))
    for n, m in names:
        print(n, "estanca" if m.is_watertight else "NO ESTANCA", round(m.volume / 1000, 1), "cm3", np.round(m.extents, 1).tolist())
    export("carcasa.stl", shell)
    export("tapa.stl", lid, shift=(0, 0, ZD), flip_z=True)
    export("cubierta_bolsa.stl", cover, shift=(0, 0, -Q["cover_z0"]))
    trimesh.util.concatenate([shell, lid, cover]).export(OUT / "ensamblado.stl")
    nx, ny, cx = Q["node_x"], Q["node_y"], Q["pcb_cx"]
    env = {
        "PCB (placa)": box(cx - 50, cx + 50, -50, 50, Q["pcb_z"], Q["pcb_top"]),
        "PCB (componentes)": box(cx - 47.5, cx + 47.5, -46.8, 46.8, Q["pcb_top"], Q["zone_top"]),
        "NodeMCU (placa+conectores)": box(nx - 15.5, nx + 15.5, ny - 29, ny + 29, Q["node_zb"], Q["node_zt"]),
        "NodeMCU (ESP-12 y USB)": trimesh.util.concatenate([box(nx - 6, nx + 6, ny - 2, ny + 14, Q["node_zb"] - 3.0, Q["node_zb"]),
                                                            box(nx - 3, nx + 3, ny - 29, ny - 21, Q["node_zb"] - 2.8, Q["node_zb"])]),
        "DHT22": box(Q["dht_x"] - Q["dht_w"] / 2, Q["dht_x"] + Q["dht_w"] / 2, Q["dht_y"] - Q["dht_l"] / 2, Q["dht_y"] + Q["dht_l"] / 2, W, W + 1.6 + Q["dht_t"]),
        "pantalla": box(-Q["disp_w"] / 2, Q["disp_w"] / 2, -Q["disp_h"] / 2, Q["disp_h"] / 2, Q["disp_z0"], ZL),
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
