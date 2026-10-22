#!/usr/bin/env python3
"""Caja v8 (preliminar): SIN tapa frontal. La pantalla DWIN 5,7" va pegada sobre el borde superior
de las paredes (con una pestaña interior de 4 mm), enrasada con el contorno: 144,8 x 110,2 mm.

Capa 1 (z < 25): PCB SELV a la izquierda; columna derecha con NodeMCU (vertical, invertido, USB abajo)
y DHT22. Capa 2: cubierta de 230 V sobre la PCB (z 25-48,5) con mini-placa y 3 relés. Origen en el centro.
Pantalla DWIN 5,7" (144,8 x 110,2 x 18,9; área activa 115,2 x 86,4): SUPUESTA hasta tener el plano oficial.
Genera esquema_v8.svg y render_v8.html.
"""
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CPL = HERE.parent / "pcbway/thermostat_universal_rev_a/jlcpcb/CPL_JLCPCB.csv"

Q = dict(
    wall=2.5, floor=3.0, flange_w=4.0, flange_t=1.5,
    disp_w=144.8, disp_h=110.2, disp_t=18.9, act_w=115.2, act_h=86.4,
    pcb=100.0, pcb_t=1.6, hole_off=5.0, hole_d=3.0, standoff=6.0, zone=14.0, pcb_cx=-18.9, pcb_cy=0.0,
    # cubierta de 230 V sobre la PCB
    deck_z0=25.0, deck_t=2.0, deck_x0=-69.7, deck_x1=32.4, part_x0=32.6, part_t=3.0,
    mb_x0=-62.0, mb_x1=14.0, mb_y0=-14.0, mb_y1=50.0, mb_t=1.6, mb_post=2.0,
    mb_posts=((-58.0, -10.0), (10.0, -10.0), (-58.0, 46.0), (10.0, 46.0)),
    rel_l=29.0, rel_w=12.7, rel_h=15.7, rel_x=(-45.0, -28.0, -11.0), rel_y=12.0,
    strip_n=4, strip_pitch=5.08, strip_w=8.0, strip_h=10.0, strip_x=-28.0, strip_y=40.0,
    slot=(16.0, 31.0, -40.0, 0.0), cover_t=1.5,
    # capa 1, columna derecha
    node_l=58.0, node_w=31.0, node_pin=8.5, node_plug=9.0, node_pad=3.5, node_x=51.2, node_y=-23.1,
    dht_w=15.1, dht_l=25.1, dht_t=7.7, dht_x=61.5, dht_y=30.0, baf_y=10.75,
    pitch=6.0, slot_w=3.0,
)
Q["outer_w"], Q["outer_h"] = Q["disp_w"], Q["disp_h"]
Q["inner_w"] = Q["outer_w"] - 2 * Q["wall"]
Q["inner_h"] = Q["outer_h"] - 2 * Q["wall"]
Q["disp_z0"] = 50.0                                       # cara trasera de la pantalla = cara superior de la pestaña
Q["wall_top"] = Q["disp_z0"]
Q["depth"] = Q["disp_z0"] + Q["disp_t"]                   # profundidad total (pantalla incluida)
Q["pcb_z"] = Q["floor"] + Q["standoff"]
Q["pcb_top"] = Q["pcb_z"] + Q["pcb_t"]
Q["zone_top"] = Q["pcb_top"] + Q["zone"]
Q["deck_z1"] = Q["deck_z0"] + Q["deck_t"]
Q["mb_z0"] = Q["deck_z1"] + Q["mb_post"]
Q["rel_z0"] = Q["mb_z0"] + Q["mb_t"]
Q["rel_z1"] = Q["rel_z0"] + Q["rel_h"]
Q["cover_z0"] = 47.0
Q["cover_z1"] = Q["cover_z0"] + Q["cover_t"]
Q["node_zb"] = Q["floor"] + Q["node_pad"]
Q["node_zt"] = Q["node_zb"] + 1.6 + Q["node_pin"] + Q["node_plug"]
IX, IY = Q["inner_w"] / 2, Q["inner_h"] / 2


def cols(x0, x1, pitch, w=Q["slot_w"]):
    n = int(round((x1 - x0) / pitch)) + 1
    return [(x0 + i * pitch - w / 2, x0 + i * pitch + w / 2) for i in range(n)]


VENTS = dict(
    top=[(a, b, 30.0, 45.0) for a, b in cols(-60, 6, 6)],                  # XZ: u=x, v=z (techo de la cubierta de 230 V)
    right_dht=[(5.0, 12.0, 20.0, 40.0)],                                   # YZ: u=z, v=y (hueco único de 7 x 20 mm junto al DHT)
)


def area(lst):
    return sum((b - a) * (d - c) for a, b, c, d in lst) / 100.0


AREAS = dict(salida=area(VENTS["top"]), dht=area(VENTS["right_dht"]))
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
    W, H = 1700, 1000
    OW, OH = Q["outer_w"], Q["outer_h"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="DejaVu Sans, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         t_(30, 38, f"Termostato ESP8266 v8 (preliminar) – {OW:.1f} × {OH:.1f} mm (= contorno de la pantalla) × {Q['depth']:.1f} mm · sin tapa frontal", 22, "start", weight="bold"),
         t_(30, 60, "La pantalla DWIN 5,7\" (144,8 × 110,2 × 18,9; supuesta) se pega sobre el borde superior de las paredes. Resto de módulos genéricos.", 12, "start", "#555")]

    def mk(ox, oy):
        return lambda x, y: (ox + (x + OW / 2) * S, oy + (OH / 2 - y) * S)

    ox, oy = 60, 120
    p = mk(ox, oy)
    o.append(t_(ox + OW * S / 2, oy - 34, "① Interior (sin pantalla): capa 1 y cubierta de 230 V", 14, weight="bold"))
    o.append(r_(ox, oy, OW * S, OH * S, fill="#e8eaee", stroke="#000", stroke_width=1.5))
    x, y = p(-IX, IY)
    o.append(r_(x, y, Q["inner_w"] * S, Q["inner_h"] * S, fill="#dfe6df", stroke="#555"))
    x, y = p(Q["pcb_cx"] - 50, Q["pcb_cy"] + 50)
    o.append(r_(x, y, 100 * S, 100 * S, fill="#1f6b3a", stroke="#000"))
    o.append(t_(*p(Q["pcb_cx"], -45), "PCB 100×100 (SELV, abajo)", 11, fill="#fff"))
    # cubierta de 230 V
    x, y = p(Q["deck_x0"], IY)
    o.append(r_(x, y, (Q["deck_x1"] - Q["deck_x0"]) * S, Q["inner_h"] * S, fill="#f3e2e2", stroke="#a33", opacity=0.55))
    x, y = p(Q["part_x0"], IY)
    o.append(r_(x, y, Q["part_t"] * S, Q["inner_h"] * S, fill="#8c8c8c", stroke="#444"))
    sx0, sx1, sy0, sy1 = Q["slot"]
    x, y = p(sx0, sy1)
    o.append(r_(x, y, (sx1 - sx0) * S, (sy1 - sy0) * S, fill="#fff", stroke="#555", stroke_dasharray="4 3"))
    o.append(t_(*p((sx0 + sx1) / 2, sy0 - 4), "paso J11–J13", 8, fill="#555"))
    x, y = p(Q["mb_x0"], Q["mb_y1"])
    o.append(r_(x, y, (Q["mb_x1"] - Q["mb_x0"]) * S, (Q["mb_y1"] - Q["mb_y0"]) * S, fill="#2f7a46", stroke="#143", stroke_width=1.5))
    for i, xs in enumerate(Q["rel_x"]):
        x, y = p(xs - Q["rel_w"] / 2, Q["rel_y"] + Q["rel_l"] / 2)
        o.append(r_(x, y, Q["rel_w"] * S, Q["rel_l"] * S, rx=2, fill="#2b4f9a", stroke="#000"))
        o.append(f'<text transform="translate({x+Q["rel_w"]*S/2+3:.1f},{y+Q["rel_l"]*S/2:.1f}) rotate(-90)" font-size="10" text-anchor="middle" fill="#fff">HF115F J{11+i}</text>')
    sl = Q["strip_n"] * Q["strip_pitch"]
    x, y = p(Q["strip_x"] - sl / 2, Q["strip_y"] + Q["strip_w"] / 2)
    o.append(r_(x, y, sl * S, Q["strip_w"] * S, fill="#4a8a3c", stroke="#222"))
    o.append(t_(*p(Q["strip_x"], Q["strip_y"] - 1), "L COMP CALOR VENT", 7, fill="#fff"))
    o.append(t_(*p(-60, IY - 3), "CUBIERTA 230 V (z 25–48,5)", 9, "start", "#a33", "bold"))
    # columna derecha, capa 1
    cx, cy = Q["node_x"], Q["node_y"]
    x, y = p(cx - Q["node_w"] / 2, cy + Q["node_l"] / 2)
    o.append(r_(x, y, Q["node_w"] * S, Q["node_l"] * S, fill="#1b2f78", stroke="#000"))
    o.append(f'<text transform="translate({x+Q["node_w"]*S/2+4:.1f},{y+Q["node_l"]*S/2:.1f}) rotate(-90)" font-size="10" text-anchor="middle" fill="#fff">NodeMCU (invertido, USB ↓)</text>')
    x, y = p(Q["dht_x"] - Q["dht_w"] / 2, Q["dht_y"] + Q["dht_l"] / 2)
    o.append(r_(x, y, Q["dht_w"] * S, Q["dht_l"] * S, fill="#f2f2f2", stroke="#2c4f9a", stroke_width=2))
    o.append(t_(x + Q["dht_w"] * S / 2, y + Q["dht_l"] * S / 2, "DHT22", 10, fill="#2c4f9a"))
    x, y = p(Q["part_x0"] + Q["part_t"], Q["baf_y"] + 0.75)
    o.append(r_(x, y, (IX - Q["part_x0"] - Q["part_t"]) * S, 1.5 * S, fill="#9fc4e8", stroke="#06c"))
    o.append(dh(ox, ox + OW * S, oy + OH * S + 24, f"{OW:.1f}"))
    o.append(dv(ox - 22, oy, oy + OH * S, f"{OH:.1f}"))

    # ② frontal: solo pantalla enrasada
    fx = 760
    pf = lambda x, y: (fx + (x + OW / 2) * S, oy + (OH / 2 - y) * S)
    o.append(t_(fx + OW * S / 2, oy - 34, "② Frontal: la pantalla ocupa todo el contorno", 14, weight="bold"))
    o.append(r_(fx, oy, OW * S, OH * S, rx=3, fill="#111", stroke="#000", stroke_width=1.5))
    x, y = pf(-Q["act_w"] / 2, Q["act_h"] / 2)
    o.append(r_(x, y, Q["act_w"] * S, Q["act_h"] * S, fill="#0b1830", stroke="#223"))
    o.append(t_(x + Q["act_w"] * S / 2, y + Q["act_h"] * S / 2 - 6, "22,5 °C", 56, fill="#9fe8ff", weight="bold"))
    o.append(t_(x + Q["act_w"] * S / 2, y + Q["act_h"] * S / 2 + 34, "Consigna 21,0 · HEAT · WiFi OK", 20, fill="#9fe8ff"))
    o.append(dh(x, x + Q["act_w"] * S, oy - 6, f"activa {Q['act_w']}"))

    # ③ sección lateral
    sx, sy = 1330, 120
    zs = 4.6
    z_ = lambda z: sx + z * zs
    y_ = lambda y: sy + (OH / 2 - y) * S

    def yz(z0, z1, y0, y1, fill, stroke="#333"):
        o.append(r_(z_(z0), y_(y1), (z1 - z0) * zs, (y1 - y0) * S, fill=fill, stroke=stroke))

    o.append(t_(sx + 170, sy - 34, "③ Sección lateral (pared a la izquierda)", 14, weight="bold"))
    yz(0, Q["floor"], -OH / 2, OH / 2, "#bbb")
    yz(0, Q["wall_top"], IY, OH / 2, "#bbb")
    yz(0, Q["wall_top"], -OH / 2, -IY, "#bbb")
    yz(Q["wall_top"] - Q["flange_t"], Q["wall_top"], IY - Q["flange_w"], IY, "#999")
    yz(Q["wall_top"] - Q["flange_t"], Q["wall_top"], -IY, -IY + Q["flange_w"], "#999")
    yz(Q["disp_z0"], Q["depth"], -Q["disp_h"] / 2, Q["disp_h"] / 2, "#111")
    yz(Q["pcb_z"], Q["pcb_top"], -50, 50, "#1f6b3a")
    yz(Q["pcb_top"], Q["zone_top"], -50, 50, "#9fd4ad")
    yz(Q["deck_z0"], Q["deck_z1"], -IY, IY, "#777")
    yz(Q["mb_z0"], Q["rel_z0"], Q["mb_y0"], Q["mb_y1"], "#2f7a46")
    yz(Q["rel_z0"], Q["rel_z1"], Q["rel_y"] - Q["rel_l"] / 2, Q["rel_y"] + Q["rel_l"] / 2, "#2b4f9a")
    yz(Q["cover_z0"], Q["cover_z1"], -IY, IY, "#777")
    ny = Q["node_y"]
    yz(Q["node_zb"], Q["node_zb"] + 1.6, ny - Q["node_l"] / 2, ny + Q["node_l"] / 2, "#1b2f78")
    yz(Q["node_zb"] + 1.6, Q["node_zt"], ny - Q["node_l"] / 2 + 6, ny + Q["node_l"] / 2 - 6, "#8fa3d9")
    bot = sy + OH * S + 24
    o.append(dh(z_(0), z_(Q["depth"]), bot, f"profundidad total {Q['depth']:.1f}"))
    o.append(dh(z_(Q["disp_z0"]), z_(Q["depth"]), bot + 30, f"pantalla {Q['disp_t']:.1f}"))
    o.append(dh(z_(0), z_(Q["disp_z0"]), bot + 60, f"carcasa {Q['disp_z0']:.1f}"))

    tx, ty = 60, 700
    rows = [
        ("Caja exterior", f"{OW:.1f} × {OH:.1f} mm = contorno de la pantalla; profundidad {Q['depth']:.1f} mm (carcasa {Q['disp_z0']:.0f} + pantalla {Q['disp_t']:.1f})"),
        ("Fijación pantalla", "pegada (cinta VHB o similar) sobre las paredes y una pestaña interior de 4 × 1,5 mm; sin tapa ni marco"),
        ("Capas", "1) PCB a la izq. + NodeMCU y DHT22 a la dcha. · 2) cubierta de 230 V sobre la PCB con mini-placa y 3 relés"),
        ("Cableado pantalla", "5 V + GND, TX → D3, RX ← D4 (J10); A0 libre (USE_POT 0)"),
        ("Ventilación", f"pasiva: techo de la cubierta {AREAS['salida']:.1f} cm² · DHT {AREAS['dht']:.1f} cm² (pared derecha)"),
    ]
    o.append(t_(tx, ty - 34, "Cotas", 14, "start", weight="bold"))
    for i, (a, b) in enumerate(rows):
        yy = ty + i * 30
        o.append(r_(tx, yy - 17, 1580, 28, fill="#f6f6f6" if i % 2 == 0 else "#fff", stroke="none"))
        o.append(t_(tx + 8, yy + 2, a, 12, "start", weight="bold"))
        o.append(t_(tx + 170, yy + 2, b, 11, "start"))
    o.append("</svg>")
    return "\n".join(o)


(HERE / "esquema_v8.svg").write_text(build_svg(), encoding="utf-8")
SCENE = json.dumps(dict(Q=Q, VENTS=VENTS, AREAS=AREAS, parts=PCB_PARTS))
tpl = (HERE / "render_v8.template.html").read_text(encoding="utf-8")
(HERE / "render_v8.html").write_text(tpl.replace("__SCENE__", SCENE), encoding="utf-8")
print("ok", Q["outer_w"], Q["outer_h"], Q["depth"], {k: round(v, 1) for k, v in AREAS.items()}, "rel_z1", Q["rel_z1"], "node_zt", Q["node_zt"])
