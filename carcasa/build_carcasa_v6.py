#!/usr/bin/env python3
"""Caja v6 (preliminar): solo pantalla DWIN 7" 800x480 táctil, sin potenciómetro.

206 x 120 x 44,5 mm. Todo cabe en una sola capa detrás de la pantalla: PCB SELV a la
izquierda; a la derecha, NodeMCU (vertical, invertido, USB hacia abajo) + DHT22 abajo y la
bolsa de 230 V (3 relés HF115F) arriba, separada por tabiques. Origen x,y en el centro.

Pantalla DWIN DMG80480C070 (190,5 x 105,4 x 13,4-13,6; área activa 154,1 x 85,9) según
listados de distribuidores: SUPUESTA hasta tener el plano oficial (variante UART 04WTC).
Genera esquema_v6.svg y render_v6.html.
"""
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CPL = HERE.parent / "pcbway/thermostat_universal_rev_a/jlcpcb/CPL_JLCPCB.csv"

Q = dict(
    wall=3.0, inner_w=200.0, inner_h=114.0, lid_t=2.5, lid_in=42.0,
    pcb=100.0, pcb_t=1.6, hole_off=5.0, hole_d=3.0, standoff=6.0, floor=3.0, zone=14.0, pcb_cx=-47.0, pcb_cy=0.0,
    # bolsa de 230 V (derecha, arriba)
    part_t=3.0, part_y0=14.0, part_x0=5.0, mb_x0=14.0, mb_x1=96.0, mb_y0=18.5, mb_y1=54.5, mb_t=1.6, mb_post=4.0,
    rel_l=29.0, rel_w=12.7, rel_h=15.7, rel_x=(30.0, 48.0, 66.0), rel_y=38.0,        # relés girados: 12,7 en x, 29 en y
    strip_n=4, strip_pitch=5.08, strip_w=8.0, strip_h=10.0, strip_x=88.0, strip_y=38.0,
    cover_z0=25.5, cover_t=1.5,
    # pantalla
    disp_w=190.5, disp_h=105.4, disp_t=13.6, act_w=154.1, act_h=85.9, win_pad=0.25,
    # NodeMCU vertical invertido y DHT22
    node_l=58.0, node_w=31.0, node_pin=8.5, node_plug=9.0, node_pad=3.5, node_x=27.5, node_y=-26.0,
    dht_w=15.1, dht_l=25.1, dht_t=7.7, dht_x=65.0, dht_y=-44.3,
    slot=3.0, pitch=6.0,
)
Q["outer_w"] = Q["inner_w"] + 2 * Q["wall"]
Q["outer_h"] = Q["inner_h"] + 2 * Q["wall"]
Q["depth"] = Q["lid_in"] + Q["lid_t"]
Q["pcb_z"] = Q["floor"] + Q["standoff"]
Q["pcb_top"] = Q["pcb_z"] + Q["pcb_t"]
Q["zone_top"] = Q["pcb_top"] + Q["zone"]
Q["mb_z0"] = Q["floor"] + Q["mb_post"]
Q["rel_z0"] = Q["mb_z0"] + Q["mb_t"]
Q["rel_z1"] = Q["rel_z0"] + Q["rel_h"]
Q["cover_z1"] = Q["cover_z0"] + Q["cover_t"]
Q["disp_z0"] = Q["lid_in"] - Q["disp_t"]
Q["node_zb"] = Q["floor"] + Q["node_pad"]
Q["node_zt"] = Q["node_zb"] + 1.6 + Q["node_pin"] + Q["node_plug"]
IX, IY = Q["inner_w"] / 2, Q["inner_h"] / 2


def cols(x0, x1, pitch=Q["pitch"], w=Q["slot"]):
    n = int(round((x1 - x0) / pitch)) + 1
    return [(x0 + i * pitch - w / 2, x0 + i * pitch + w / 2) for i in range(n)]


VENTS = dict(
    top=[(a, b, 8.0, 23.0) for a, b in cols(20, 86)],                    # XZ: u=x, v=z (techo de la bolsa)
    bottom_dht=[(a, b, 4.0, 11.0) for a, b in cols(58, 72, 7)],          # XZ: u=x, v=z (suelo bajo el DHT)
)


def area(lst):
    return sum((b - a) * (d - c) for a, b, c, d in lst) / 100.0


AREAS = dict(salida=area(VENTS["top"]), dht=area(VENTS["bottom_dht"]))
parts = []
with open(CPL, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        parts.append((r["Designator"], float(r["Mid X"][:-2]), float(r["Mid Y"][:-2])))
JST = dict(J1=3, J8=3, J9=3, J2=4, J3=4, J4=4, J5=4, J6=4, J7=4, J10=5)


def kind(d):
    if d in JST:
        return dict(t="jst", n=JST[d])
    if d in ("J11", "J12", "J13"):
        return dict(t="phoenix")
    return dict(t={"R": "res", "Q": "to92", "F": "ptc"}.get(d[0], "elec" if d in ("C8", "C10") else "cer"))


PCB_PARTS = [dict(ref=d, x=x, y=y, **kind(d)) for d, x, y in parts]

# ----------------------------------------------------------------- SVG
S = 4.0


def r_(x, y, w, h, **a):
    at = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" {at}/>'


def t_(x, y, s, size=11, anchor="middle", fill="#222", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{s}</text>'


def dh(x1, x2, y, label):
    return (f'<g stroke="#b00"><line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/><line x1="{x1}" y1="{y-4}" x2="{x1}" y2="{y+4}"/>'
            f'<line x1="{x2}" y1="{y-4}" x2="{x2}" y2="{y+4}"/></g>' + t_((x1 + x2) / 2, y - 4, label, 11, fill="#b00"))


def dv(x, y1, y2, label):
    return (f'<g stroke="#b00"><line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}"/><line x1="{x-4}" y1="{y1}" x2="{x+4}" y2="{y1}"/>'
            f'<line x1="{x-4}" y1="{y2}" x2="{x+4}" y2="{y2}"/></g>'
            f'<text transform="translate({x-6},{(y1+y2)/2}) rotate(-90)" font-size="11" text-anchor="middle" fill="#b00">{label}</text>')


def build_svg():
    W, H = 1700, 1180
    OW, OH = Q["outer_w"], Q["outer_h"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="DejaVu Sans, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         t_(30, 38, f"Termostato ESP8266 v6 (preliminar) – {OW:.0f} × {OH:.0f} × {Q['depth']:.1f} mm · solo pantalla DWIN 7\" táctil · sin potenciómetro", 22, "start", weight="bold"),
         t_(30, 60, "Pantalla (190,5 × 105,4 × 13,6; área activa 154,1 × 85,9) según listados de distribuidores, sin plano oficial: SUPUESTA. Resto de módulos genéricos.", 12, "start", "#555")]

    def mk(ox, oy):
        return lambda x, y: (ox + (x + OW / 2) * S, oy + (OH / 2 - y) * S)

    ox, oy = 60, 120
    p = mk(ox, oy)
    o.append(t_(ox + OW * S / 2, oy - 34, "① Interior (sin tapa ni pantalla)", 14, weight="bold"))
    o.append(r_(ox, oy, OW * S, OH * S, fill="#e8eaee", stroke="#000", stroke_width=1.5))
    x, y = p(-IX, IY)
    o.append(r_(x, y, Q["inner_w"] * S, Q["inner_h"] * S, fill="#dfe6df", stroke="#555"))
    # bolsa 230 V
    x, y = p(Q["part_x0"] + Q["part_t"], IY)
    o.append(r_(x, y, (IX - Q["part_x0"] - Q["part_t"]) * S, (IY - Q["part_y0"] - Q["part_t"]) * S, fill="#f3e2e2", stroke="#a33"))
    x, y = p(Q["part_x0"], IY)
    o.append(r_(x, y, Q["part_t"] * S, (IY - Q["part_y0"]) * S, fill="#8c8c8c", stroke="#444"))
    x, y = p(Q["part_x0"], Q["part_y0"] + Q["part_t"])
    o.append(r_(x, y, (IX - Q["part_x0"]) * S, Q["part_t"] * S, fill="#8c8c8c", stroke="#444"))
    # PCB
    x, y = p(Q["pcb_cx"] - 50, Q["pcb_cy"] + 50)
    o.append(r_(x, y, 100 * S, 100 * S, fill="#1f6b3a", stroke="#000"))
    o.append(t_(*p(Q["pcb_cx"], 0), "PCB 100×100 (SELV)", 12, fill="#fff"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            px_, py_ = p(Q["pcb_cx"] + sx * 45, Q["pcb_cy"] + sy * 45)
            o.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="{1.5*S:.1f}" fill="#fff" stroke="#000"/>')
    # mini-placa y relés
    x, y = p(Q["mb_x0"], Q["mb_y1"])
    o.append(r_(x, y, (Q["mb_x1"] - Q["mb_x0"]) * S, (Q["mb_y1"] - Q["mb_y0"]) * S, fill="#2f7a46", stroke="#143", stroke_width=1.5))
    for i, xs in enumerate(Q["rel_x"]):
        x, y = p(xs - Q["rel_w"] / 2, Q["rel_y"] + Q["rel_l"] / 2)
        o.append(r_(x, y, Q["rel_w"] * S, Q["rel_l"] * S, rx=2, fill="#2b4f9a", stroke="#000"))
        o.append(f'<text transform="translate({x+Q["rel_w"]*S/2+3:.1f},{y+Q["rel_l"]*S/2:.1f}) rotate(-90)" font-size="10" text-anchor="middle" fill="#fff">HF115F J{11+i}</text>')
    x, y = p(Q["strip_x"] - Q["strip_w"] / 2, Q["strip_y"] + Q["strip_n"] * Q["strip_pitch"] / 2)
    o.append(r_(x, y, Q["strip_w"] * S, Q["strip_n"] * Q["strip_pitch"] * S, fill="#4a8a3c", stroke="#222"))
    o.append(t_(*p(Q["strip_x"], Q["mb_y1"] + 1.5), "bornas", 8, fill="#a33"))
    o.append(t_(*p(55, Q["mb_y1"] + 1.5), "BOLSA 230 V (tabiques; cubierta propia)", 10, fill="#a33", weight="bold"))
    # NodeMCU vertical
    cx, cy = Q["node_x"], Q["node_y"]
    x, y = p(cx - Q["node_w"] / 2, cy + Q["node_l"] / 2)
    o.append(r_(x, y, Q["node_w"] * S, Q["node_l"] * S, fill="#1b2f78", stroke="#000"))
    o.append(f'<text transform="translate({x+Q["node_w"]*S/2+4:.1f},{y+Q["node_l"]*S/2:.1f}) rotate(-90)" font-size="10" text-anchor="middle" fill="#fff">NodeMCU (invertido, USB ↓ pared inferior)</text>')
    x, y = p(Q["dht_x"] - Q["dht_w"] / 2, Q["dht_y"] + Q["dht_l"] / 2)
    o.append(r_(x, y, Q["dht_w"] * S, Q["dht_l"] * S, fill="#f2f2f2", stroke="#2c4f9a", stroke_width=2))
    o.append(t_(x + Q["dht_w"] * S / 2, y + Q["dht_l"] * S / 2, "DHT22", 10, fill="#2c4f9a"))
    x, y = p(48, -22)
    o.append(r_(x, y, 1.5 * S, 34 * S, fill="#9fc4e8", stroke="#06c"))
    o.append(dh(ox, ox + OW * S, oy + OH * S + 24, f"{OW:.0f}"))
    o.append(dv(ox - 22, oy, oy + OH * S, f"{OH:.0f}"))

    # ② frontal
    fy = oy + OH * S + 70
    pf = lambda x, y: (ox + (x + OW / 2) * S, fy + (OH / 2 - y) * S)
    o.append(t_(ox + OW * S / 2, fy - 20, "② Frontal: solo pantalla (sin mando)", 14, weight="bold"))
    o.append(r_(ox, fy, OW * S, OH * S, rx=5, fill="#d6d9de", stroke="#000", stroke_width=1.5))
    ww, wh = Q["act_w"] + 2 * Q["win_pad"], Q["act_h"] + 2 * Q["win_pad"]
    x, y = pf(-ww / 2, wh / 2)
    o.append(r_(x, y, ww * S, wh * S, fill="#0b1830", stroke="#000"))
    o.append(t_(x + ww * S / 2, y + wh * S / 2 - 6, "22,5 °C", 64, fill="#9fe8ff", weight="bold"))
    o.append(t_(x + ww * S / 2, y + wh * S / 2 + 40, "Consigna 21,0 · HEAT · WiFi OK", 22, fill="#9fe8ff"))
    o.append(dh(x, x + ww * S, fy - 3, f"ventana {ww:.1f}"))

    # ③ sección lateral
    sx, sy = 1010, 120
    zs = 6.0
    z_ = lambda z: sx + z * zs
    y_ = lambda y: sy + (OH / 2 - y) * S

    def yz(z0, z1, y0, y1, fill, stroke="#333"):
        o.append(r_(z_(z0), y_(y1), (z1 - z0) * zs, (y1 - y0) * S, fill=fill, stroke=stroke))

    o.append(t_(sx + 140, sy - 34, "③ Sección lateral (pared a la izquierda)", 14, weight="bold"))
    yz(0, 3, -OH / 2, OH / 2, "#bbb")
    yz(0, Q["lid_in"], IY, OH / 2, "#bbb")
    yz(0, Q["lid_in"], -OH / 2, -IY, "#bbb")
    yz(Q["lid_in"], Q["depth"], -OH / 2, OH / 2, "#aaa")
    yz(Q["disp_z0"], Q["lid_in"], -Q["disp_h"] / 2, Q["disp_h"] / 2, "#111")
    yz(Q["pcb_z"], Q["pcb_top"], -50, 50, "#1f6b3a")
    yz(Q["pcb_top"], Q["zone_top"], -50, 50, "#9fd4ad")
    yz(Q["mb_z0"], Q["rel_z0"], Q["mb_y0"], Q["mb_y1"], "#2f7a46")
    yz(Q["rel_z0"], Q["rel_z1"], Q["rel_y"] - Q["rel_l"] / 2, Q["rel_y"] + Q["rel_l"] / 2, "#2b4f9a")
    yz(Q["cover_z0"], Q["cover_z1"], Q["part_y0"] + Q["part_t"], IY, "#777")
    ny = Q["node_y"]
    yz(Q["node_zb"], Q["node_zb"] + 1.6, ny - Q["node_l"] / 2, ny + Q["node_l"] / 2, "#1b2f78")
    yz(Q["node_zb"] + 1.6, Q["node_zt"], ny - Q["node_l"] / 2 + 6, ny + Q["node_l"] / 2 - 6, "#8fa3d9")
    bot = sy + OH * S + 24
    o.append(dh(z_(0), z_(Q["depth"]), bot, f"profundidad {Q['depth']:.1f}"))
    o.append(dh(z_(Q["disp_z0"]), z_(Q["lid_in"]), bot + 30, f"pantalla {Q['disp_t']:.1f}"))
    o.append(dh(z_(0), z_(Q["disp_z0"]), bot + 60, f"internos {Q['disp_z0']:.1f}"))

    tx, ty = 1010, 760
    rows = [
        ("Caja exterior", f"{OW:.0f} × {OH:.0f} × {Q['depth']:.1f} mm, sin mando ni saliente"),
        ("Pantalla", f"DWIN 7\" 800×480 táctil: {Q['disp_w']} × {Q['disp_h']} × {Q['disp_t']}, activa {Q['act_w']} × {Q['act_h']} (supuesto)"),
        ("Superficie útil", f"{Q['act_w']*Q['act_h']/100:.0f} cm² (v5: 50 cm², v1: 2 OLED ≈ 12 cm²)"),
        ("Cableado", "5 V + GND, TX → D3, RX ← D4 (J10); A0 libre (USE_POT 0)"),
        ("Ventilación", f"pasiva: techo bolsa {AREAS['salida']:.1f} cm² · DHT {AREAS['dht']:.1f} cm²"),
    ]
    o.append(t_(tx, ty - 34, "Cotas", 14, "start", weight="bold"))
    for i, (a, b) in enumerate(rows):
        yy = ty + i * 30
        o.append(r_(tx, yy - 17, 640, 28, fill="#f6f6f6" if i % 2 == 0 else "#fff", stroke="none"))
        o.append(t_(tx + 8, yy + 2, a, 12, "start", weight="bold"))
        o.append(t_(tx + 130, yy + 2, b, 11, "start"))
    o.append("</svg>")
    return "\n".join(o)


(HERE / "esquema_v6.svg").write_text(build_svg(), encoding="utf-8")
SCENE = json.dumps(dict(Q=Q, VENTS=VENTS, AREAS=AREAS, parts=PCB_PARTS))
tpl = (HERE / "render_v6.template.html").read_text(encoding="utf-8")
(HERE / "render_v6.html").write_text(tpl.replace("__SCENE__", SCENE), encoding="utf-8")
print("ok", Q["outer_w"], Q["outer_h"], Q["depth"], {k: round(v, 1) for k, v in AREAS.items()}, "disp_z0", Q["disp_z0"], "node_zt", Q["node_zt"])
