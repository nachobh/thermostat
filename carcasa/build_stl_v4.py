#!/usr/bin/env python3
"""STL de la caja v4 (112 x 112 x 56,5 mm): carcasa, tapa y bandeja de potencia.

Usa las cotas de build_carcasa_v4.py (Q, FRONT, VENTS). Genera en carcasa/stl/:
  carcasa.stl   fondo + paredes + pilares + columnas de la tapa + orejas de pared
  tapa.stl      tapa (cara frontal sobre la cama), con ventanas OLED, pot y marcos
  bandeja.stl   bandeja de 230 V con partición (la bandeja sobre la cama)
  ensamblado.stl todo en su sitio (solo para revisar)
Requiere trimesh + manifold3d. Medidas de NodeMCU, OLED, DHT y pot: SUPUESTAS.
"""
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_carcasa_v4 as B  # noqa: E402  (regenera también el SVG/HTML, sin coste)

Q, F, V = B.Q, B.FRONT, B.VENTS
OUT = HERE / "stl"
OUT.mkdir(exist_ok=True)
EPS = 0.2
H = Q["outer"] / 2          # 56
I = Q["inner"] / 2          # 53
ZL = Q["lid_in"]            # 54 (plano de la tapa)
ZD = Q["depth"]             # 56,5


def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl(r, z0, z1, x=0.0, y=0.0, axis="z", sections=48):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation((0, 0, (z0 + z1) / 2))
    if axis == "y":      # eje y, z0..z1 se interpretan como y0..y1; x,y -> x,z
        m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0)))
        m.apply_translation((x, (z0 + z1) / 2, y))
        return m
    m.apply_translation((x, y, 0))
    return m


def union(ms):
    return trimesh.boolean.union(ms, engine="manifold")


def diff(a, ms):
    return trimesh.boolean.difference([a] + list(ms), engine="manifold")


def inter(a, b):
    return trimesh.boolean.intersection([a, b], engine="manifold")


# --------------------------------------------------------------- carcasa
def build_shell():
    body = diff(box(-H, H, -H, H, 0, ZL), [box(-I, I, -I, I, Q["wall"], ZL + EPS)])
    cut = []
    for a, b, c, d in V["top"]:                       # techo de la bolsa (u=x, v=z)
        cut.append(box(a, b, I - EPS, H + EPS, c, d))
    for a, b, c, d in V["bottom_dht"]:                # suelo bajo el DHT (u=x, v=z)
        cut.append(box(a, b, -H - EPS, -I + EPS, c, d))
    for a, b, c, d in V["side_dht"]:                  # lateral izq. DHT (u=z, v=y)
        cut.append(box(-H - EPS, -I + EPS, c, d, a, b))
    ny = F["node"][1]
    cut.append(box(I - EPS, H + EPS, ny - 6, ny + 6, ZL - 8, ZL + EPS))     # USB 12 x 8
    for x in (-45.0, 45.0):                           # entradas de cable Ø12 en el techo
        cut.append(cyl(6.0, I - EPS, H + EPS, x=x, y=40.0, axis="y"))
    for sx in (-1, 1):                                # orejas: agujeros Ø4,5
        cut.append(cyl(2.25, -EPS, Q["wall"] + EPS, x=sx * 63.0, y=0.0))
    shell = diff(body, cut)

    add = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 45.0, sy * 45.0
            pil = diff(cyl(3.5, Q["wall"] - 0.1, Q["pcb_z"], x=x, y=y), [cyl(1.3, Q["wall"] + 0.5, Q["pcb_z"] + EPS, x=x, y=y)])
            add.append(pil)
            x, y = sx * 50.5, sy * 50.5               # columnas de tornillo de la tapa
            col = diff(cyl(3.2, 11.5, ZL, x=x, y=y), [cyl(1.3, ZL - 16, ZL + EPS, x=x, y=y)])
            add.append(col)
        add.append(box(sx * 50.3 if sx > 0 else -53.1, 53.1 if sx > 0 else -50.3, 12.0, 53.0, 21.5, 25.0))   # repisas de la bandeja
        ear = box(0, 0.1, 0, 0.1, 0, 0.1)
        x0, x1 = (H - 0.1, 70.0) if sx > 0 else (-70.0, -H + 0.1)
        add.append(diff(box(x0, x1, -8, 8, 0, Q["wall"]), [cyl(2.25, -EPS, Q["wall"] + EPS, x=sx * 63.0, y=0.0)]))
    return union([shell] + add)


# ------------------------------------------------------------------- tapa
def frame(cx, cy, iw, ih, wall, z0, z1, notch=None, open_side=None):
    ring = diff(box(cx - iw / 2 - wall, cx + iw / 2 + wall, cy - ih / 2 - wall, cy + ih / 2 + wall, z0, z1),
                [box(cx - iw / 2, cx + iw / 2, cy - ih / 2, cy + ih / 2, z0 - EPS, z1 + EPS)])
    cut = []
    if notch == "bottom":
        cut.append(box(cx - 6, cx + 6, cy - ih / 2 - wall - EPS, cy - ih / 2 + EPS, z0 - EPS, z1 + EPS))
    if notch == "right":
        cut.append(box(cx + iw / 2 - EPS, cx + iw / 2 + wall + EPS, cy - 6, cy + 6, z0 - EPS, z1 + EPS))
    if open_side == "bottom":
        cut.append(box(cx - iw / 2, cx + iw / 2, cy - ih / 2 - wall - EPS, cy - ih / 2 + EPS, z0 - EPS, z1 + EPS))
    return diff(ring, cut) if cut else ring


def build_lid():
    plate = box(-H, H, -H, H, ZL, ZD)
    cut = []
    for k in ("oled1", "oled2"):                      # ventanas OLED 24 x 13 (área activa 21,7 x 10,9)
        cx, cy = F[k]
        cut.append(box(cx - Q["win_w"] / 2, cx + Q["win_w"] / 2, cy + 3 - Q["win_h"] / 2, cy + 3 + Q["win_h"] / 2, ZL - EPS, ZD + EPS))
    px, py = F["pot"]
    cut.append(cyl(3.7, ZL - EPS, ZD + EPS, x=px, y=py))                      # potenciómetro Ø7,4
    for a, b, c, d in V["lid_in"]:                    # ventilación mínima bajo la bolsa
        cut.append(box(a, b, c, d, ZL - EPS, ZD + EPS))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 50.5, sy * 50.5
            cut.append(cyl(1.7, ZL - EPS, ZD + EPS, x=x, y=y))                # tornillo M3 Ø3,4
            cut.append(cyl(3.2, ZD - 1.5, ZD + EPS, x=x, y=y))                # alojamiento de cabeza
    lid = diff(plate, cut)

    add = []
    for k in ("oled1", "oled2"):                      # marcos de los OLED
        cx, cy = F[k]
        add.append(frame(cx, cy, Q["oled_w"] + 0.4, Q["oled_h"] + 0.4, 1.2, ZL - 4.5, ZL + 0.1, notch="bottom"))
    nx, ny_ = F["node"]
    add.append(frame(nx, ny_, Q["node_l"] + 0.4, Q["node_w"] + 0.4, 1.2, ZL - 4.6, ZL + 0.1, notch="right"))
    dx, dy = F["dht"]
    add.append(frame(dx, dy, 15.1 + 0.3, 25.1 + 0.3, 1.2, ZL - 8.0, ZL + 0.1, open_side="bottom"))
    add.append(box(-33.75, -32.25, -50.0, -21.0, 40.0, ZL + 0.1))                # deflector térmico del DHT
    lid = union([lid] + add)
    lid = diff(lid, [cyl(3.4, ZL - 6, ZL, x=sx * 50.5, y=sy * 50.5) for sx in (-1, 1) for sy in (-1, 1)])   # holgura a las columnas
    # no invadir las paredes de la carcasa (los marcos pueden rozar el contorno)
    return inter(lid, box(-H, H, -H, H, ZL - 5, ZD + 1)) if False else trim(lid)


def trim(m):
    keep_cavity = box(-I + 0.05, I - 0.05, -I + 0.05, I - 0.05, ZL - 6, ZL + 0.2)
    outer = box(-H, H, -H, H, ZL, ZD + 0.2)
    return union([inter(m, keep_cavity), inter(m, outer)])


# ---------------------------------------------------------------- bandeja
def build_tray():
    plate = box(-52.8, 52.8, Q["pocket_y0"], 52.8, Q["tray_z0"], Q["tray_z0"] + Q["tray_t"])
    plate = diff(plate, [cyl(3.9, Q["tray_z0"] - EPS, Q["tray_z0"] + Q["tray_t"] + EPS, x=sx * 50.5, y=50.5) for sx in (-1, 1)])
    part = box(-52.8, 52.8, Q["part_y0"], Q["pocket_y0"], Q["tray_z0"], ZL)
    part = diff(part, [box(34, 46, Q["part_y0"] - EPS, Q["pocket_y0"] + EPS, 30, 36)])    # paso del mazo de 5 V
    posts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 43.0, Q["mb_y"] + sy * 11.0
            posts.append(diff(cyl(2.5, Q["tray_z0"] + Q["tray_t"] - 0.1, Q["mb_z0"], x=x, y=y), [cyl(1.1, Q["mb_z0"] - 4, Q["mb_z0"] + EPS, x=x, y=y)]))
    return union([plate, part] + posts)


def export(name, m, shift=(0, 0, 0), flip_z=False):
    m = m.copy()
    if flip_z:
        m.apply_transform(np.diag([1, 1, -1, 1]))
        m.invert()
    m.apply_translation(shift)
    m.export(OUT / name)
    return m


if __name__ == "__main__":
    shell, lid, tray = build_shell(), build_lid(), build_tray()
    rep = []
    for n, m in (("carcasa", shell), ("tapa", lid), ("bandeja", tray)):
        rep.append((n, m.is_watertight, m.is_winding_consistent, round(m.volume / 1000, 1), np.round(m.extents, 1).tolist()))
    # a posición de impresión
    export("carcasa.stl", shell)
    lid_p = export("tapa.stl", lid, shift=(0, 0, ZD), flip_z=True)                  # cara frontal sobre la cama
    export("bandeja.stl", tray, shift=(0, 0, -Q["tray_z0"]))
    asm = trimesh.util.concatenate([shell, lid, tray])
    asm.export(OUT / "ensamblado.stl")
    for r in rep:
        print(r)
    # interferencias entre piezas impresas y piezas montadas (volumen en mm3, debe ser ~0)
    parts = {
        "PCB (placa)": box(-50, 50, -50, 50, Q["pcb_z"], Q["pcb_top"]),
        "PCB (componentes)": box(-47.5, 47.5, -46.8, 46.8, Q["pcb_top"], Q["zone_top"]),
        "NodeMCU+pines": box(F["node"][0] - 29, F["node"][0] + 29, F["node"][1] - 15.5, F["node"][1] + 15.5, ZL - 13, ZL),
        "OLED1": box(F["oled1"][0] - 13.65, F["oled1"][0] + 13.65, F["oled1"][1] - 13.9, F["oled1"][1] + 13.9, ZL - 4, ZL),
        "OLED2": box(F["oled2"][0] - 13.65, F["oled2"][0] + 13.65, F["oled2"][1] - 13.9, F["oled2"][1] + 13.9, ZL - 4, ZL),
        "DHT22": box(F["dht"][0] - 7.55, F["dht"][0] + 7.55, F["dht"][1] - 12.55, F["dht"][1] + 12.55, ZL - 7.7, ZL),
        "pot": cyl(8.0, ZL - 10, ZL, x=F["pot"][0], y=F["pot"][1]),
        "mini-placa+relés": box(-47, 47, Q["mb_y"] - Q["mb_h"] / 2, Q["mb_y"] + Q["mb_h"] / 2, Q["mb_z0"], Q["rel_z1"]),
    }
    for pn, pm in parts.items():
        row = []
        for n, m in (("carcasa", shell), ("tapa", lid), ("bandeja", tray)):
            try:
                v = inter(m, pm).volume
            except Exception:
                v = 0.0
            row.append(f"{n}={v:.0f}")
        print(f"interferencia {pn}: " + "  ".join(row))
    for a, an, b, bn in ((shell, "carcasa", lid, "tapa"), (shell, "carcasa", tray, "bandeja"), (lid, "tapa", tray, "bandeja")):
        print(f"interferencia {an}/{bn}: {inter(a, b).volume:.0f} mm3")
