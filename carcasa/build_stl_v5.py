#!/usr/bin/env python3
"""STL de la caja v5 (preliminar): carcasa, tapa, cubierta (bandeja SELV/230 V) y cubierta de bolsa.

Cotas de build_carcasa_v5.py. Salida en carcasa/stl_v5/. Pantalla, NodeMCU, DHT y mini-placa
son medidas SUPUESTAS; repasar con las piezas reales (y el plano mecánico de DWIN).
"""
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_carcasa_v5 as B  # noqa: E402
from build_stl_v4 import box, cyl, union, diff, inter  # noqa: E402

Q, F, V = B.Q, B.FRONT, B.VENTS
OUT = HERE / "stl_v5"
OUT.mkdir(exist_ok=True)
EPS = 0.2
H, I, ZL, ZD = Q["outer"] / 2, Q["inner"] / 2, Q["lid_in"], Q["depth"]
def sbox(x0, x1, y0, y1, z0, z1):
    return box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z1)


COL = [(sx * 50.5, sy * 50.5) for sx in (-1, 1) for sy in (-1, 1)]


def build_shell():
    body = diff(box(-H, H, -H, H, 0, ZL), [box(-I, I, -I, I, Q["wall"], ZL + EPS)])
    ny = F["node"][1]
    cut = []
    cut += [box(a, b, I - EPS, H + EPS, c, d) for a, b, c, d in V["top"]]
    cut += [box(a, b, -H - EPS, -I + EPS, c, d) for a, b, c, d in V["bottom_dht"]]
    cut += [box(-H - EPS, -I + EPS, c, d, a, b) for a, b, c, d in V["side_dht"]]
    cut += [box(I - EPS, H + EPS, c, d, a, b) for a, b, c, d in V["side_pow"]]
    cut.append(box(I - EPS, H + EPS, ny - 6, ny + 6, 28, 34))                 # USB 12 x 6
    cut += [cyl(6.0, I - EPS, H + EPS, x=x, y=38.0, axis="y") for x in (-45.0, 45.0)]   # entradas de cable Ø12
    cut += [cyl(2.25, -EPS, Q["wall"] + EPS, x=sx * 63.0, y=0.0) for sx in (-1, 1)]
    shell = diff(body, cut)
    add = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 45.0, sy * 45.0
            add.append(diff(cyl(3.5, Q["wall"] - 0.1, Q["pcb_z"], x=x, y=y), [cyl(1.3, Q["wall"] + 0.5, Q["pcb_z"] + EPS, x=x, y=y)]))
        add.append(diff(cyl(3.2, 11.5, ZL, x=sx * 50.5, y=50.5), [cyl(1.3, ZL - 16, ZL + EPS, x=sx * 50.5, y=50.5)]))
        add.append(diff(cyl(3.2, 11.5, ZL, x=sx * 50.5, y=-50.5), [cyl(1.3, ZL - 16, ZL + EPS, x=sx * 50.5, y=-50.5)]))
        xa, xb = (50.3, 53.1) if sx > 0 else (-53.1, -50.3)
        add.append(box(xa, xb, -50.0, 50.0, Q["tray_z0"] - 3.5, Q["tray_z0"]))                 # repisa de la cubierta
        add.append(box(xa, xb, 15.0, 46.0, Q["cover_z0"] - 3.5, Q["cover_z0"]))                # repisa de la cubierta de bolsa
        x0, x1 = (H - 0.1, 70.0) if sx > 0 else (-70.0, -H + 0.1)
        add.append(diff(box(x0, x1, -8, 8, 0, Q["wall"]), [cyl(2.25, -EPS, Q["wall"] + EPS, x=sx * 63.0, y=0.0)]))
    return union([shell] + add)


def build_lid():
    plate = box(-H, H, -H, H, ZL, ZD)
    ww, wh = Q["act_w"] + 2 * Q["win_pad"], Q["act_h"] + 2 * Q["win_pad"]
    cx, cy = Q["disp_cx"], Q["disp_cy"]
    cut = [box(cx - ww / 2, cx + ww / 2, cy - wh / 2, cy + wh / 2, ZL - EPS, ZD + EPS),
           cyl(Q["pot_hole"] / 2 + 0.2, ZL - EPS, ZD + EPS, x=F["pot"][0], y=F["pot"][1])]
    for x, y in COL:
        cut += [cyl(1.7, ZL - EPS, ZD + EPS, x=x, y=y), cyl(3.2, ZD - 1.5, ZD + EPS, x=x, y=y)]
    lid = diff(plate, cut)
    dw, dh = Q["disp_w"] + 0.4, Q["disp_h"] + 0.4
    rim = diff(box(cx - dw / 2 - 1.2, cx + dw / 2 + 1.2, cy - dh / 2 - 1.2, cy + dh / 2 + 1.2, ZL - 3.0, ZL + 0.1),
               [box(cx - dw / 2, cx + dw / 2, cy - dh / 2, cy + dh / 2, ZL - 3.2, ZL + 0.2)])
    # el marco deja pasos de cable de 10 mm en el centro de cada lado corto y largo
    rim = diff(rim, [box(cx - 5, cx + 5, cy - dh / 2 - 1.4, cy - dh / 2 + 0.1, ZL - 3.2, ZL + 0.2),
                     box(cx - dw / 2 - 1.4, cx - dw / 2 + 0.1, cy - 5, cy + 5, ZL - 3.2, ZL + 0.2)])
    lid = union([lid, rim])
    lid = diff(lid, [cyl(3.4, ZL - 6, ZL, x=x, y=y) for x, y in COL])
    return inter(lid, box(-H, H, -H, H, ZL - 6, ZD + 1))


def build_deck():
    z0, z1 = Q["tray_z0"], Q["deck_z"]
    plate = box(-52.8, 52.8, -52.8, 52.8, z0, z1)
    plate = diff(plate, [box(-45, -5, -8, 0, z0 - EPS, z1 + EPS), box(5, 45, -8, 0, z0 - EPS, z1 + EPS)] +
                 [cyl(3.9, z0 - EPS, z1 + EPS, x=x, y=y) for x, y in COL])
    part = box(-52.8, 52.8, Q["part_y0"], Q["pocket_y0"], z0, Q["cover_z0"])
    part = diff(part, [box(34, 46, Q["part_y0"] - EPS, Q["pocket_y0"] + EPS, 28, 35)])
    add = [plate, part]
    for sx in (-1, 1):
        for sy in (-1, 1):                                                                     # postes de la mini-placa
            x, y = sx * 43.0, Q["mb_y"] + sy * 11.0
            add.append(diff(cyl(2.5, z1 - 0.1, Q["mb_z0"], x=x, y=y), [cyl(1.1, Q["mb_z0"] - 4, Q["mb_z0"] + EPS, x=x, y=y)]))
    nx, ny = F["node"]
    for dx in (-26, 26):
        for dy in (-12.5, 12.5):
            add.append(box(nx + dx - 3, nx + dx + 3, ny + dy - 3, ny + dy + 3, z1 - 0.1, z1 + Q["node_pad"]))   # apoyos
    for sx in (-1, 1):                                                                         # esquineros del NodeMCU
        for sy in (-1, 1):
            cxp, cyp = nx + sx * (Q["node_l"] / 2 + 0.2), ny + sy * (Q["node_w"] / 2 + 0.2)
            zt_ = Q["node_zb"] + 3.0
            add.append(sbox(cxp, cxp - sx * 8, cyp, cyp + sy * 1.2, z1 - 0.1, zt_))          # lado largo, hacia dentro
            if not (sx > 0 and sy < 0):                                                       # esquina junto a la columna de tapa
                add.append(sbox(cxp, cxp + sx * 1.2, cyp, cyp - sy * 8, z1 - 0.1, zt_))       # lado corto, hacia dentro
    dx_, dy_ = F["dht"]                                                                        # DHT22: retén en L (lados +y y +x)
    hw, hl = Q["dht_w"] / 2, Q["dht_l"] / 2
    add.append(sbox(dx_ - hw - 1.2, dx_ + hw + 1.4, dy_ + hl + 0.2, dy_ + hl + 1.4, z1 - 0.1, z1 + 6))
    add.append(sbox(dx_ + hw + 0.2, dx_ + hw + 1.4, dy_ - hl - 1.2, dy_ + hl + 1.4, z1 - 0.1, z1 + 6))
    add.append(box(-33.75, -32.25, -50.0, -21.0, z1 - 0.1, 45.0))                              # deflector térmico
    return union(add)


def build_cover():
    z0, z1 = Q["cover_z0"], Q["cover_z1"]
    plate = box(-52.8, 52.8, Q["pocket_y0"] + 0.2, 52.8, z0, z1)
    return diff(plate, [cyl(3.9, z0 - EPS, z1 + EPS, x=sx * 50.5, y=50.5) for sx in (-1, 1)])


def export(name, m, shift=(0, 0, 0), flip_z=False):
    m = m.copy()
    if flip_z:
        m.apply_transform(np.diag([1, 1, -1, 1]))
        m.invert()
    m.apply_translation(shift)
    m.export(OUT / name)


if __name__ == "__main__":
    shell, lid, deck, cover = build_shell(), build_lid(), build_deck(), build_cover()
    for n, m in (("carcasa", shell), ("tapa", lid), ("cubierta", deck), ("cubierta_bolsa", cover)):
        print(n, "estanca" if m.is_watertight else "NO ESTANCA", round(m.volume / 1000, 1), "cm3", np.round(m.extents, 1).tolist())
    export("carcasa.stl", shell)
    export("tapa.stl", lid, shift=(0, 0, ZD), flip_z=True)
    export("cubierta.stl", deck, shift=(0, 0, -Q["tray_z0"]))
    export("cubierta_bolsa.stl", cover, shift=(0, 0, -Q["cover_z0"]))
    trimesh.util.concatenate([shell, lid, deck, cover]).export(OUT / "ensamblado.stl")
    nx, ny = F["node"]
    env = {
        "PCB (placa)": box(-50, 50, -50, 50, Q["pcb_z"], Q["pcb_top"]),
        "PCB (componentes)": box(-47.5, 47.5, -46.8, 46.8, Q["pcb_top"], Q["zone_top"]),
        "NodeMCU (placa+conectores)": box(nx - 29, nx + 29, ny - 15.5, ny + 15.5, Q["node_zb"], Q["node_zt"]),
        "NodeMCU (ESP-12 y USB)": trimesh.util.concatenate([box(nx - 2, nx + 14, ny - 6, ny + 6, Q["node_zb"] - 3.0, Q["node_zb"]),
                                                            box(nx + 21, nx + 29, ny - 3, ny + 3, Q["node_zb"] - 2.8, Q["node_zb"])]),
        "DHT22": box(F["dht"][0] - Q["dht_w"] / 2, F["dht"][0] + Q["dht_w"] / 2, F["dht"][1] - Q["dht_l"] / 2, F["dht"][1] + Q["dht_l"] / 2, Q["deck_z"], Q["deck_z"] + 1.6 + Q["dht_t"]),
        "pantalla": box(Q["disp_cx"] - Q["disp_w"] / 2, Q["disp_cx"] + Q["disp_w"] / 2, Q["disp_cy"] - Q["disp_h"] / 2, Q["disp_cy"] + Q["disp_h"] / 2, Q["disp_z0"], ZL),
        "pot": cyl(Q["pot_body"] / 2, ZL - Q["pot_len"], ZL, x=F["pot"][0], y=F["pot"][1]),
        "mini-placa+relés": box(-47, 47, Q["mb_y"] - Q["mb_h"] / 2, Q["mb_y"] + Q["mb_h"] / 2, Q["mb_z0"], Q["rel_z1"]),
    }
    names = (("carcasa", shell), ("tapa", lid), ("cubierta", deck), ("cubierta_bolsa", cover))
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
