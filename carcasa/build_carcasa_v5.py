#!/usr/bin/env python3
"""Caja v5 (preliminar): pantalla DWIN 4" 480x480 UART en el frontal + 3 relés HF115F.

112 x 112 x 66,5 mm. Capas en Z desde la pared: PCB SELV -> bandeja (cubierta completa,
z 25-27) con NodeMCU (invertido), DHT22 y la bolsa de 230 V (y > 15) -> cubierta de la
bolsa -> pantalla (13,4 mm) -> tapa. Origen x,y en el centro de la caja.

Medidas de la pantalla (90,6 x 86,1 x 13,4; área activa 71,9 x 70,2) tomadas de listados
de distribuidores del DWIN DMG48480C040_03WTC (sin la hoja oficial): SUPUESTAS.
Genera esquema_v5.svg y render_v5.html.
"""
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CPL = HERE.parent / "pcbway/thermostat_universal_rev_a/jlcpcb/CPL_JLCPCB.csv"

Q = dict(
    wall=3.0, inner=106.0, lid_t=2.5, lid_in=64.0,
    pcb=100.0, pcb_t=1.6, hole_off=5.0, hole_d=3.0, standoff=6.0, floor=3.0, zone=14.0,
    tray_z0=25.0, tray_t=2.0, pocket_y0=15.0, part_t=3.0,
    rel_l=29.0, rel_w=12.7, rel_h=15.7, rel_x=(-32.0, 0.0, 32.0), rel_y=44.0,
    mb_w=94.0, mb_h=28.0, mb_y=37.5, mb_t=1.6, mb_post=2.0,
    strip_n=4, strip_pitch=5.08, strip_w=8.0, strip_h=10.0, strip_y=27.5,
    cover_t=1.5,
    disp_w=90.6, disp_h=86.1, disp_t=13.4, disp_cx=0.0, disp_cy=7.0, act_w=71.9, act_h=70.2, win_pad=0.25,
    node_l=58.0, node_w=31.0, node_pin=8.5, node_plug=9.0, node_pad=3.5,
    dht_w=15.1, dht_l=25.1, dht_t=7.7,
    pot_body=15.0, pot_len=10.0, pot_hole=7.0, knob_d=14.0, knob_h=15.0,
    slot=3.0, pitch=6.0,
)
Q["outer"] = Q["inner"] + 2 * Q["wall"]
Q["depth"] = Q["lid_in"] + Q["lid_t"]                 # 66,5
Q["pcb_z"] = Q["floor"] + Q["standoff"]
Q["pcb_top"] = Q["pcb_z"] + Q["pcb_t"]
Q["zone_top"] = Q["pcb_top"] + Q["zone"]              # 24,6
Q["part_y0"] = Q["pocket_y0"] - Q["part_t"]
Q["deck_z"] = Q["tray_z0"] + Q["tray_t"]              # 27
Q["mb_z0"] = Q["deck_z"] + Q["mb_post"]
Q["rel_z0"] = Q["mb_z0"] + Q["mb_t"]
Q["rel_z1"] = Q["rel_z0"] + Q["rel_h"]                # 46,3
Q["cover_z0"] = 47.0                                  # sobre la partición y las repisas
Q["cover_z1"] = Q["cover_z0"] + Q["cover_t"]          # 48,5
Q["disp_z0"] = Q["lid_in"] - Q["disp_t"]              # 50,6
Q["node_zb"] = Q["deck_z"] + Q["node_pad"]            # base de la placa NodeMCU invertida: 30,5
Q["node_zt"] = Q["node_zb"] + 1.6 + Q["node_pin"] + Q["node_plug"]   # 49,6
FRONT = dict(pot=(35.0, -45.2), node=(18.0, -34.0), dht=(-43.0, -33.5))


def cols(x0, x1, pitch=Q["pitch"], w=Q["slot"]):
    n = int(round((x1 - x0) / pitch)) + 1
    return [(x0 + i * pitch - w / 2, x0 + i * pitch + w / 2) for i in range(n)]


VENTS = dict(
    top=[(a, b, 30.0, 46.0) for a, b in cols(-36, 36)],                # XZ: u=x, v=z (techo de la bolsa)
    side_pow=[(a, b, 17.0, 24.0) for a, b in cols(31, 43, 6)],         # YZ: u=z, v=y (entrada baja de la bolsa)
    bottom_dht=[(a, b, 28.0, 36.0) for a, b in cols(-49, -37, 6)],     # XZ: u=x, v=z
    side_dht=[(a, b, -44.0, -29.0) for a, b in cols(29.5, 35.5, 3)],   # YZ: u=z, v=y
)


def area(lst, n=1):
    return n * sum((b - a) * (d - c) for a, b, c, d in lst) / 100.0


AREAS = dict(salida=area(VENTS["top"]), entrada=area(VENTS["side_pow"], 2), dht=area(VENTS["bottom_dht"]) + area(VENTS["side_dht"]))

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
S = 4.6


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
    W, H = 1800, 1240
    O = Q["outer"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="DejaVu Sans, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         t_(30, 38, f"Termostato ESP8266 v5 (preliminar) – 112 × 112 × {Q['depth']:.1f} mm · pantalla DWIN 4\" 480×480 UART · 3 relés HF115F", 22, "start", weight="bold"),
         t_(30, 60, "Pantalla (90,6 × 86,1 × 13,4; área activa 71,9 × 70,2) según listados de distribuidores, sin la hoja oficial: SUPUESTA. Resto de módulos también genéricos.", 12, "start", "#555")]

    def mk(ox, oy):
        return lambda x, y: (ox + (x + O / 2) * S, oy + (O / 2 - y) * S)

    # ---- ① cubierta de la bandeja (sin cubierta de bolsa ni tapa)
    ox, oy = 80, 120
    p = mk(ox, oy)
    o.append(t_(ox + O * S / 2, oy - 34, "① Cubierta SELV/230 V (sin tapa ni pantalla)", 14, weight="bold"))
    o.append(r_(ox, oy, O * S, O * S, fill="#e8eaee", stroke="#000", stroke_width=1.5))
    x, y = p(-53, 53)
    o.append(r_(x, y, 106 * S, 106 * S, fill="#dfe6df", stroke="#555"))
    x, y = p(-53, 53)
    o.append(r_(x, y, 106 * S, (53 - Q["pocket_y0"]) * S, fill="#f3e2e2", stroke="#a33"))
    x, y = p(-53, Q["pocket_y0"])
    o.append(r_(x, y, 106 * S, Q["part_t"] * S, fill="#8c8c8c", stroke="#444"))
    for xa, xb in ((-45, -5), (5, 45)):                           # pasos de mazo
        x, y = p(xa, -4)
        o.append(r_(x, y, (xb - xa) * S, 8 * S, fill="#fff", stroke="#555", stroke_dasharray="4 3"))
    o.append(t_(*p(0, -8), "pasos de mazos (PCB ↔ cubierta)", 9, fill="#555"))
    cx, cy = FRONT["node"]
    x, y = p(cx - Q["node_l"] / 2, cy + Q["node_w"] / 2)
    o.append(r_(x, y, Q["node_l"] * S, Q["node_w"] * S, fill="#1b2f78", stroke="#000"))
    o.append(t_(x + Q["node_l"] * S / 2, y + Q["node_w"] * S / 2 + 4, "NodeMCU (invertido, USB → pared dcha.)", 10, fill="#fff"))
    cx, cy = FRONT["dht"]
    x, y = p(cx - Q["dht_w"] / 2, cy + Q["dht_l"] / 2)
    o.append(r_(x, y, Q["dht_w"] * S, Q["dht_l"] * S, fill="#f2f2f2", stroke="#2c4f9a", stroke_width=2))
    o.append(t_(x + Q["dht_w"] * S / 2, y + Q["dht_l"] * S / 2 + 3, "DHT22", 10, fill="#2c4f9a"))
    x, y = p(-33.75, -21)
    o.append(r_(x, y, 1.5 * S, 29 * S, fill="#9fc4e8", stroke="#06c"))
    x, y = p(-Q["mb_w"] / 2, Q["mb_y"] + Q["mb_h"] / 2)
    o.append(r_(x, y, Q["mb_w"] * S, Q["mb_h"] * S, fill="#2f7a46", stroke="#143", stroke_width=1.5))
    for i, xs in enumerate(Q["rel_x"]):
        x, y = p(xs - Q["rel_l"] / 2, Q["rel_y"] + Q["rel_w"] / 2)
        o.append(r_(x, y, Q["rel_l"] * S, Q["rel_w"] * S, rx=2, fill="#2b4f9a", stroke="#000"))
        o.append(t_(x + Q["rel_l"] * S / 2, y + Q["rel_w"] * S / 2 + 4, f"HF115F  J{11+i}", 9, fill="#fff"))
    x, y = p(-Q["strip_n"] * Q["strip_pitch"] / 2, Q["strip_y"] + Q["strip_w"] / 2)
    o.append(r_(x, y, Q["strip_n"] * Q["strip_pitch"] * S, Q["strip_w"] * S, fill="#4a8a3c", stroke="#222"))
    o.append(t_(*p(0, Q["strip_y"] - 1), "L  COMP  CALOR  VENT", 8, fill="#fff"))
    o.append(t_(*p(-51, 50), "BOLSA 230 V (cubierta propia z 47–48,5)", 10, "start", "#a33", "bold"))
    o.append(dh(ox, ox + O * S, oy + O * S + 24, f"{O:.0f}"))
    o.append(dv(ox - 22, oy, oy + O * S, f"{O:.0f}"))

    # ---- ② tapa con pantalla
    fx = 740
    pf = mk(fx, oy)
    o.append(t_(fx + O * S / 2, oy - 34, "② Tapa frontal con pantalla", 14, weight="bold"))
    o.append(r_(fx, oy, O * S, O * S, rx=5, fill="#d6d9de", stroke="#000", stroke_width=1.5))
    dcx, dcy = Q["disp_cx"], Q["disp_cy"]
    x, y = pf(dcx - Q["disp_w"] / 2, dcy + Q["disp_h"] / 2)
    o.append(r_(x, y, Q["disp_w"] * S, Q["disp_h"] * S, fill="none", stroke="#888", stroke_dasharray="5 3"))
    ww, wh = Q["act_w"] + 2 * Q["win_pad"], Q["act_h"] + 2 * Q["win_pad"]
    x, y = pf(dcx - ww / 2, dcy + wh / 2)
    o.append(r_(x, y, ww * S, wh * S, fill="#0b1830", stroke="#000"))
    o.append(t_(x + ww * S / 2, y + wh * S / 2 - 10, "22,5 °C", 40, fill="#9fe8ff", weight="bold"))
    o.append(t_(x + ww * S / 2, y + wh * S / 2 + 24, "HEAT · AUTO · WiFi", 18, fill="#9fe8ff"))
    px_, py_ = pf(*FRONT["pot"])
    o.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="{Q["knob_d"]/2*S:.1f}" fill="#555" stroke="#222"/>')
    o.append(dh(*(pf(dcx - ww / 2, 0)[0], pf(dcx + ww / 2, 0)[0]), oy + 24, f"ventana {ww:.1f}"))
    o.append(dv(fx + O * S + 20, pf(0, dcy + wh / 2)[1], pf(0, dcy - wh / 2)[1], f"{wh:.1f}"))
    o.append(t_(fx + O * S / 2, oy + O * S + 24, "Potenciómetro (Ø7,4, mando Ø14) bajo la pantalla; sin OLED", 11, fill="#444"))

    # ---- ③ sección lateral
    sx, sy = 1340, 120
    zs = 4.6
    z_ = lambda z: sx + z * zs
    y_ = lambda y: sy + (O / 2 - y) * S

    def yz(z0, z1, y0, y1, fill, stroke="#333"):
        o.append(r_(z_(z0), y_(y1), (z1 - z0) * zs, (y1 - y0) * S, fill=fill, stroke=stroke))

    o.append(t_(sx + 170, sy - 34, "③ Sección lateral (pared a la izquierda)", 14, weight="bold"))
    yz(0, 3, -56, 56, "#bbb")
    yz(0, Q["lid_in"], 53, 56, "#bbb")
    yz(0, Q["lid_in"], -56, -53, "#bbb")
    yz(Q["lid_in"], Q["depth"], -56, 56, "#aaa")
    yz(Q["tray_z0"], Q["deck_z"], -53, 53, "#777")
    yz(Q["tray_z0"], Q["cover_z0"], Q["part_y0"], Q["pocket_y0"], "#777")
    yz(Q["cover_z0"], Q["cover_z1"], Q["pocket_y0"], 53, "#777")
    yz(Q["mb_z0"], Q["rel_z0"], Q["mb_y"] - Q["mb_h"] / 2, Q["mb_y"] + Q["mb_h"] / 2, "#2f7a46")
    yz(Q["rel_z0"], Q["rel_z1"], Q["rel_y"] - Q["rel_w"] / 2, Q["rel_y"] + Q["rel_w"] / 2, "#2b4f9a")
    yz(Q["pcb_z"], Q["pcb_top"], -50, 50, "#1f6b3a")
    yz(Q["pcb_top"], Q["zone_top"], -50, 50, "#9fd4ad")
    ny = FRONT["node"][1]
    yz(Q["node_zb"], Q["node_zb"] + 1.6, ny - 15.5, ny + 15.5, "#1b2f78")
    yz(Q["node_zb"] + 1.6, Q["node_zt"], ny - 12.5, ny + 12.5, "#8fa3d9")
    yz(Q["disp_z0"], Q["lid_in"], Q["disp_cy"] - Q["disp_h"] / 2, Q["disp_cy"] + Q["disp_h"] / 2, "#111")
    yz(Q["lid_in"] - Q["pot_len"], Q["lid_in"], FRONT["pot"][1] - 7.5, FRONT["pot"][1] + 7.5, "#888")
    yz(Q["depth"], Q["depth"] + Q["knob_h"], FRONT["pot"][1] - 7, FRONT["pot"][1] + 7, "#444")
    bot = sy + O * S + 24
    o.append(dh(z_(0), z_(Q["depth"]), bot, f"profundidad {Q['depth']:.1f}"))
    o.append(dh(z_(Q["disp_z0"]), z_(Q["lid_in"]), bot + 30, f"pantalla {Q['disp_t']:.1f}"))
    o.append(dh(z_(Q["deck_z"]), z_(Q["disp_z0"]), bot + 60, f"cubierta→pantalla {Q['disp_z0']-Q['deck_z']:.1f}"))
    o.append(dh(z_(Q["depth"]), z_(Q["depth"] + Q["knob_h"]), bot + 90, f"mando +{Q['knob_h']:.0f}"))

    tx, ty = 80, 830
    rows = [
        ("Caja exterior", f"{O:.0f} × {O:.0f} × {Q['depth']:.1f} mm (+{Q['knob_h']:.0f} del mando)"),
        ("Pantalla", f"DWIN 4\" 480×480 UART/táctil: {Q['disp_w']} × {Q['disp_h']} × {Q['disp_t']} mm, área activa {Q['act_w']} × {Q['act_h']} (supuesto)"),
        ("Cableado pantalla", "4 hilos: 5 V (de Vin del NodeMCU), GND, TX → D3/GPIO0, RX ← D4/GPIO2 (por J10; sustituye a los pulsadores)"),
        ("Pila en Z", "PCB 25 · cubierta 2 · NodeMCU+pines+conectores 22,6 · holgura 1 · pantalla 13,4 · tapa 2,5"),
        ("Bolsa de 230 V", "y > 15 mm, cubierta propia a z 47–48,5; relés HF115F con diodo en cada bobina"),
        ("Ventilación", f"pasiva: techo bolsa {AREAS['salida']:.0f} cm² · laterales {AREAS['entrada']:.0f} cm² · DHT {AREAS['dht']:.1f} cm²"),
        ("NodeMCU / DHT22", "sobre la cubierta (NodeMCU invertido sobre 4 apoyos de 3,5 mm; DHT22 plano con deflector)"),
    ]
    o.append(t_(tx, ty - 34, "Cotas", 14, "start", weight="bold"))
    for i, (a, b) in enumerate(rows):
        yy = ty + i * 30
        o.append(r_(tx, yy - 17, 1650, 28, fill="#f6f6f6" if i % 2 == 0 else "#fff", stroke="none"))
        o.append(t_(tx + 8, yy + 2, a, 12, "start", weight="bold"))
        o.append(t_(tx + 220, yy + 2, b, 12, "start"))
    o.append("</svg>")
    return "\n".join(o)


(HERE / "esquema_v5.svg").write_text(build_svg(), encoding="utf-8")
SCENE = json.dumps(dict(Q=Q, FRONT=FRONT, VENTS=VENTS, AREAS=AREAS, parts=PCB_PARTS))
tpl = (HERE / "render_v5.template.html").read_text(encoding="utf-8")
(HERE / "render_v5.html").write_text(tpl.replace("__SCENE__", SCENE), encoding="utf-8")
print("ok", Q["outer"], Q["depth"], {k: round(v, 1) for k, v in AREAS.items()}, "disp_z0", Q["disp_z0"], "node_zt", Q["node_zt"])
