#!/usr/bin/env python3
"""Caja v4: 112 x 112 x 56,5 mm. SELV (PCB, NodeMCU, DHT, OLED, pot) + 3 relés Hongfa HF115F/005-1ZS3.

Los SSR van en una bolsa de 230 V arriba (bandeja a z=25, partición lateral a y=+18),
encima de la zona alta de la PCB. Origen x,y en el centro de la caja; z desde la pared.
Genera esquema_v4.svg y render_v4.html. Medidas de SSR (18x24x4, dato del usuario),
disipador, DHT22, NodeMCU y OLED son SUPUESTAS salvo las que dé la ficha real.
"""
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CPL = HERE.parent / "pcbway/thermostat_universal_rev_a/jlcpcb/CPL_JLCPCB.csv"

Q = dict(
    wall=3.0, inner=106.0, lid_t=2.5, depth=56.5,
    # PCB SELV
    pcb=100.0, pcb_t=1.6, hole_off=5.0, hole_d=3.0, standoff=6.0, floor=3.0, zone=14.0,
    # bolsa 230 V
    tray_z0=25.0, tray_t=2.0, pocket_y0=15.0, part_t=3.0,
    rel_l=29.0, rel_w=12.7, rel_h=15.7, rel_x=(-32.0, 0.0, 32.0), rel_y=44.0,   # HF115F/005-1ZS3
    mb_w=94.0, mb_h=28.0, mb_y=37.5, mb_t=1.6, mb_post=2.0,                    # mini-placa de potencia
    strip_n=4, strip_pitch=5.08, strip_w=8.0, strip_h=10.0, strip_y=27.5,
    # tapa
    node_l=58.0, node_w=31.0, node_h=13.0,
    oled_w=27.3, oled_h=27.8, oled_t=4.0, win_w=24.0, win_h=13.0,
    pot_body=16.0, pot_len=10.0, pot_hole=7.0, knob_d=20.0, knob_h=15.0,
    slot=3.0, pitch=6.0,
)
Q["outer"] = Q["inner"] + 2 * Q["wall"]               # 112
Q["lid_in"] = Q["depth"] - Q["lid_t"]                 # 54
Q["pcb_z"] = Q["floor"] + Q["standoff"]               # 9
Q["pcb_top"] = Q["pcb_z"] + Q["pcb_t"]                # 10.6
Q["zone_top"] = Q["pcb_top"] + Q["zone"]              # 24.6
Q["pocket_y1"] = Q["inner"] / 2                       # 53
Q["part_y0"] = Q["pocket_y0"] - Q["part_t"]           # 18
Q["pocket_h"] = Q["pocket_y1"] - Q["pocket_y0"]       # 32
Q["mb_z0"] = Q["tray_z0"] + Q["tray_t"] + Q["mb_post"]    # 29
Q["rel_z0"] = Q["mb_z0"] + Q["mb_t"]                     # 30,6
Q["rel_z1"] = Q["rel_z0"] + Q["rel_h"]                   # 46,3
FRONT = dict(oled1=(-38.0, -4.0), oled2=(-7.0, -4.0), pot=(32.0, -4.0),
             node=(18.0, -36.5), dht=(-43.0, -33.5))


def cols(x0, x1, pitch=Q["pitch"], w=Q["slot"]):
    n = int(round((x1 - x0) / pitch)) + 1
    return [(x0 + i * pitch - w / 2, x0 + i * pitch + w / 2) for i in range(n)]


VENTS = dict(
    top=[(a, b, 30.0, 46.0) for a, b in cols(-36, 36)],                 # XZ: u=x, v=z (techo de la bolsa)
    lid_in=[(a, b, 17.0, 24.0) for a, b in cols(-36, 36)],              # XY: u=x, v=y (tapa, base de la bolsa)
    bottom_dht=[(a, b, 42.0, 52.0) for a, b in cols(-49, -37, 6)],      # XZ: u=x, v=z
    side_dht=[(a, b, -44.0, -29.0) for a, b in cols(43.5, 51.5, 4)],    # YZ: u=z, v=y
)


def area(lst, n=1):
    return n * sum((b - a) * (d - c) for a, b, c, d in lst) / 100.0


AREAS = dict(salida=area(VENTS["top"]), entrada=area(VENTS["lid_in"]),
             dht=area(VENTS["bottom_dht"]) + area(VENTS["side_dht"]))

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
    W, H = 1750, 1180
    O = Q["outer"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="DejaVu Sans, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#06c"/></marker>'
         '<marker id="ar2" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#d33"/></marker></defs>',
         t_(30, 38, "Termostato ESP8266 v4 (definitivo) – 112 × 112 × 56,5 mm · 3 relés Hongfa HF115F · DHT junto al NodeMCU", 22, "start", weight="bold"),
         t_(30, 60, "Relé HF115F: 29 × 12,7 × 15,7 mm (listados de distribuidores, sin la hoja de Hongfa). DHT, NodeMCU, OLED y mini-placa SUPUESTOS: presentar las piezas reales antes de imprimir.", 12, "start", "#555")]

    def mk(ox, oy):
        return lambda x, y: (ox + (x + O / 2) * S, oy + (O / 2 - y) * S)

    # ---- ① interior sin tapa
    ox, oy = 80, 120
    p = mk(ox, oy)
    o.append(t_(ox + O * S / 2, oy - 34, "① Interior (sin tapa) – alzado frontal", 14, weight="bold"))
    o.append(r_(ox, oy, O * S, O * S, fill="#e8eaee", stroke="#000", stroke_width=1.5))
    x, y = p(-53, 53)
    o.append(r_(x, y, 106 * S, 106 * S, fill="#dfe6df", stroke="#555"))
    x, y = p(-53, 53)
    o.append(r_(x, y, 106 * S, Q["pocket_h"] * S, fill="#f3e2e2", stroke="#a33"))
    x, y = p(-53, Q["pocket_y0"])
    o.append(r_(x, y, 106 * S, Q["part_t"] * S, fill="#8c8c8c", stroke="#444"))
    x, y = p(-50, 50)
    o.append(r_(x, y, 100 * S, 100 * S, fill="none", stroke="#1f6b3a", stroke_width=2, stroke_dasharray="6 4"))
    o.append(t_(*p(-3, 12), "PCB 100×100 debajo", 10, fill="#1f6b3a"))
    # fila A: OLED + pot
    for k in ("oled1", "oled2"):
        cx, cy = FRONT[k]
        x, y = p(cx - Q["oled_w"] / 2, cy + Q["oled_h"] / 2)
        o.append(r_(x, y, Q["oled_w"] * S, Q["oled_h"] * S, fill="#151a30", stroke="#000"))
        x, y = p(cx - 10.9, cy + 3 + 5.4)
        o.append(r_(x, y, 21.7 * S, 10.9 * S, fill="#9fe8ff", stroke="none", opacity=0.8))
    cx, cy = FRONT["pot"]
    x, y = p(cx, cy)
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{Q["knob_d"]/2*S:.1f}" fill="#bbb" stroke="#333"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{Q["pot_body"]/2*S:.1f}" fill="#888"/>')
    # fila B: DHT + baffle + NodeMCU
    cx, cy = FRONT["node"]
    x, y = p(cx - Q["node_l"] / 2, cy + Q["node_w"] / 2)
    o.append(r_(x, y, Q["node_l"] * S, Q["node_w"] * S, fill="#1b2f78", stroke="#000"))
    o.append(t_(x + Q["node_l"] * S / 2, y + Q["node_w"] * S / 2 + 4, "NodeMCU (USB → pared dcha.)", 10, fill="#fff"))
    cx, cy = FRONT["dht"]
    x, y = p(cx - 7.55, cy + 12.55)
    o.append(r_(x, y, 15.1 * S, 25.1 * S, fill="#f2f2f2", stroke="#2c4f9a", stroke_width=2))
    o.append(t_(x + 7.55 * S, y + 12.5 * S, "DHT22", 10, fill="#2c4f9a"))
    x, y = p(-33.0, -21)
    o.append(r_(x, y, 1.5 * S, 31 * S, fill="#9fc4e8", stroke="#06c"))
    # mini-placa de potencia + 3 relés + bornas
    x, y = p(-Q["mb_w"] / 2, Q["mb_y"] + Q["mb_h"] / 2)
    o.append(r_(x, y, Q["mb_w"] * S, Q["mb_h"] * S, fill="#2f7a46", stroke="#143", stroke_width=1.5))
    for i, xs in enumerate(Q["rel_x"]):
        x, y = p(xs - Q["rel_l"] / 2, Q["rel_y"] + Q["rel_w"] / 2)
        o.append(r_(x, y, Q["rel_l"] * S, Q["rel_w"] * S, rx=2, fill="#2b4f9a", stroke="#000"))
        o.append(t_(x + Q["rel_l"] * S / 2, y + Q["rel_w"] * S / 2 + 4, f"HF115F  J{11+i}", 9, fill="#fff"))
        for dx in (-9, -4):
            px_, py_ = p(xs + dx, Q["rel_y"] - Q["rel_w"] / 2 - 3)
            o.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="3" fill="#d8c070" stroke="#222"/>')
        o.append(t_(*p(xs - 6.5, Q["rel_y"] - Q["rel_w"] / 2 - 7), "bobina+diodo", 8, fill="#fff"))
    x, y = p(-Q["strip_n"] * Q["strip_pitch"] / 2, Q["strip_y"] + Q["strip_w"] / 2)
    o.append(r_(x, y, Q["strip_n"] * Q["strip_pitch"] * S, Q["strip_w"] * S, fill="#4a8a3c", stroke="#222"))
    o.append(t_(x + Q["strip_n"] * Q["strip_pitch"] * S / 2, y + Q["strip_w"] * S / 2 + 3, "L  COMP  CALOR  VENT", 8, fill="#fff"))
    for xs in Q["rel_x"]:
        a1, a2 = p(xs, Q["pocket_y0"] + 1), p(xs, Q["pocket_y0"] + 8)
        o.append(f'<line x1="{a1[0]:.1f}" y1="{a1[1]:.1f}" x2="{a2[0]:.1f}" y2="{a2[1]:.1f}" stroke="#06c" stroke-width="2" marker-end="url(#ar)"/>')
    o.append(t_(*p(-51, 50), "BOLSA 230 V (partición 3 mm, mini-placa ≥ 8 mm de la SELV)", 10, "start", "#a33", "bold"))
    o.append(dh(ox, ox + O * S, oy + O * S + 24, f"{O:.0f}"))
    o.append(dv(ox - 22, oy, oy + O * S, f"{O:.0f}"))
    xa, ya = p(Q["rel_x"][1] - Q["rel_l"] / 2, 0)
    o.append(dh(xa, xa + Q["rel_l"] * S, oy + O * S + 48, f"relé {Q['rel_l']:.0f}"))
    o.append(t_(ox + O * S / 2, oy + O * S + 74, "Azul: ventilación pasiva mínima (la bolsa casi no disipa calor)", 11, fill="#444"))

    # ---- ② tapa
    fx = 740
    pf = mk(fx, oy)
    o.append(t_(fx + O * S / 2, oy - 34, "② Tapa frontal", 14, weight="bold"))
    o.append(r_(fx, oy, O * S, O * S, rx=5, fill="#d6d9de", stroke="#000", stroke_width=1.5))
    for a, b, c, d in VENTS["lid_in"]:
        x, y = pf(a, d)
        o.append(r_(x, y, (b - a) * S, (d - c) * S, fill="#222"))
    for k in ("oled1", "oled2"):
        cx, cy = FRONT[k]
        x, y = pf(cx - Q["win_w"] / 2, cy + 3 + Q["win_h"] / 2)
        o.append(r_(x, y, Q["win_w"] * S, Q["win_h"] * S, fill="#111"))
    x, y = pf(*FRONT["pot"])
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{Q["knob_d"]/2*S:.1f}" fill="#555" stroke="#222"/>')
    o.append(t_(fx + O * S / 2, oy + O * S + 24, "Rendijas de ventilación mínima bajo la bolsa de 230 V (13×)", 11, fill="#444"))
    o.append(dh(*(pf(FRONT["oled1"][0] - Q["oled_w"] / 2, 0)[0], pf(FRONT["oled1"][0] + Q["oled_w"] / 2, 0)[0]), oy + 20, "27,3"))

    # ---- ③ sección lateral
    sx, sy = 1380, 120
    zs = 4.6 * 1.0
    z_ = lambda z: sx + z * zs
    y_ = lambda y: sy + (O / 2 - y) * S

    def yz(z0, z1, y0, y1, fill, stroke="#333"):
        o.append(r_(z_(z0), y_(y1), (z1 - z0) * zs, (y1 - y0) * S, fill=fill, stroke=stroke))

    o.append(t_(sx + 120, sy - 34, "③ Sección lateral (pared a la izquierda)", 14, weight="bold"))
    yz(0, 3, -56, 56, "#bbb")
    yz(0, Q["lid_in"], 53, 56, "#bbb")
    yz(0, Q["lid_in"], -56, -53, "#bbb")
    yz(Q["lid_in"], Q["depth"], -56, 56, "#aaa")
    yz(Q["tray_z0"], Q["tray_z0"] + Q["tray_t"], Q["pocket_y0"], 53, "#777")
    yz(Q["tray_z0"], Q["lid_in"], Q["part_y0"], Q["pocket_y0"], "#777")
    yz(Q["tray_z0"] + Q["tray_t"], Q["mb_z0"], Q["mb_y"] - Q["mb_h"] / 2, Q["mb_y"] + Q["mb_h"] / 2, "#999")
    yz(Q["mb_z0"], Q["rel_z0"], Q["mb_y"] - Q["mb_h"] / 2, Q["mb_y"] + Q["mb_h"] / 2, "#2f7a46")
    yz(Q["rel_z0"], Q["rel_z1"], Q["rel_y"] - Q["rel_w"] / 2, Q["rel_y"] + Q["rel_w"] / 2, "#2b4f9a")
    yz(Q["pcb_z"], Q["pcb_top"], -50, 50, "#1f6b3a")
    yz(Q["pcb_top"], Q["zone_top"], -50, 50, "#9fd4ad")
    yz(Q["lid_in"] - Q["node_h"], Q["lid_in"], FRONT["node"][1] - 15.5, FRONT["node"][1] + 15.5, "#4a7bd0")
    yz(Q["lid_in"] - 7.7, Q["lid_in"], FRONT["dht"][1] - 12.5, FRONT["dht"][1] + 12.5, "#e8e8e8")
    yz(Q["lid_in"] - Q["pot_len"], Q["lid_in"], -3 - 8, -3 + 8, "#888")
    yz(Q["depth"], Q["depth"] + Q["knob_h"], -13, 7, "#444")
    bot = sy + O * S + 24
    o.append(dh(z_(0), z_(Q["depth"]), bot, f"profundidad {Q['depth']:.0f}"))
    o.append(dh(z_(Q["tray_z0"]), z_(Q["rel_z1"]), bot + 30, f"bandeja+placa+relé {Q['rel_z1']-Q['tray_z0']:.1f}"))
    o.append(dh(z_(Q["rel_z1"]), z_(Q["lid_in"]), bot + 60, f"holgura {Q['lid_in']-Q['rel_z1']:.1f}"))
    o.append(dh(z_(Q["depth"]), z_(Q["depth"] + Q["knob_h"]), bot + 90, f"mando +{Q['knob_h']:.0f}"))

    # ---- tabla
    tx, ty = 80, 800
    rows = [
        ("Caja exterior", f"{O:.0f} × {O:.0f} × {Q['depth']:.0f} mm (+{Q['knob_h']:.0f} del mando)"),
        ("Pila en Z", "pared 3 · sep. 6 · PCB 1,6 · comp./mazos 14 · bandeja 2 · poste 2 · mini-placa 1,6 · relé 15,7 · holgura 7,7"),
        ("Bolsa de 230 V", f"{Q['inner']:.0f} × {Q['pocket_h']:.0f} mm interior, arriba, sobre la zona alta de la PCB"),
        ("Relés ×3 (HF115F/005-1ZS3)", "29 × 12,7 × 15,7 mm · SPDT 16 A 250 VAC · bobina 5 V 62 Ω ≈ 80 mA (diodo 1N4007 en cada bobina)"),
        ("Ventilación", f"pasiva mínima: techo de la bolsa {AREAS['salida']:.0f} cm² + base {AREAS['entrada']:.0f} cm² (sin disipadores)"),
        ("DHT22", f"izquierda del NodeMCU, deflector entre ambos, {AREAS['dht']:.1f} cm² de rendijas propias"),
        ("NodeMCU", "58 × 31 mm, USB hacia la pared derecha (abertura 12 × 8 mm)"),
    ]
    o.append(t_(tx, ty - 34, "Cotas y ventilación", 14, "start", weight="bold"))
    for i, (a, b) in enumerate(rows):
        yy = ty + i * 30
        o.append(r_(tx, yy - 17, 1250, 28, fill="#f6f6f6" if i % 2 == 0 else "#fff", stroke="none"))
        o.append(t_(tx + 8, yy + 2, a, 12, "start", weight="bold"))
        o.append(t_(tx + 210, yy + 2, b, 12, "start"))
    o.append("</svg>")
    return "\n".join(o)


(HERE / "esquema_v4.svg").write_text(build_svg(), encoding="utf-8")
SCENE = json.dumps(dict(Q=Q, FRONT=FRONT, VENTS=VENTS, AREAS=AREAS, parts=PCB_PARTS))
tpl = (HERE / "render_v4.template.html").read_text(encoding="utf-8")
(HERE / "render_v4.html").write_text(tpl.replace("__SCENE__", SCENE), encoding="utf-8")
print("ok", Q["outer"], Q["depth"], {k: round(v, 1) for k, v in AREAS.items()}, "rel_z1", Q["rel_z1"])
