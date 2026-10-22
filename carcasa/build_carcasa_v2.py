#!/usr/bin/env python3
"""Caja v2: electrónica SELV (abajo) + 3 SSR con disipador y DHT (arriba/derecha).

Genera esquema_v2.svg y render_v2.html. Cotas en mm, origen x en el centro de la
caja e y desde la base. Medidas de SSR-40DA, disipador, DHT22, NodeMCU y OLED son
SUPUESTAS (genéricas): sustituirlas por las de las piezas reales.
"""
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CPL = HERE.parent / "pcbway/thermostat_universal_rev_a/jlcpcb/CPL_JLCPCB.csv"

Q = dict(
    wall=3.0, bar=3.0, w_in=172.0, h_selv=106.0, h_pow=136.0,
    # pila en Z desde la pared
    fin_gap=8.0, fin_h=25.0, base_t=4.0, ssr_h=23.0, cover_gap=10.0, lid_t=2.5,
    # SSR / disipador / bornas
    ssr_l=62.0, ssr_w=45.0, hs_w=50.0, hs_h=100.0, n_fins=9, fin_t=2.0,
    ssr_x=(-55.0, 0.0, 55.0), ssr_names=("COMP J11", "CALOR J12", "VENT J13"),
    strip_bottom=22.0, strip_top=14.0,
    # SELV
    pcb=100.0, pcb_t=1.6, hole_off=5.0, hole_d=3.0, standoff=6.0, floor=3.0, zone=14.0,
    node_l=58.0, node_w=31.0, node_h=13.0,
    oled_w=27.3, oled_h=27.8, oled_t=4.0, win_w=24.0, win_h=13.0,
    pot_body=16.0, pot_len=10.0, pot_hole=7.0, knob_d=20.0, knob_h=15.0,
    cluster_x=-33.0,                    # centro de PCB/tapa SELV respecto al eje de la caja
    # DHT
    dht_box=(26.0, 84.0, 3.0, 45.0),    # x0,x1,y0,y1 de la cámara (coord. caja)
    # ventilación
    slot=3.0, pitch=7.0,
)
Q["w_out"] = Q["w_in"] + 2 * Q["wall"]
Q["h_out"] = Q["wall"] + Q["h_selv"] + Q["bar"] + Q["h_pow"] + Q["wall"]
Q["y_bar0"] = Q["wall"] + Q["h_selv"]               # 109
Q["y_pow0"] = Q["y_bar0"] + Q["bar"]                # 112
Q["y_pow1"] = Q["y_pow0"] + Q["h_pow"]              # 248
Q["z_hs0"] = Q["fin_gap"]                           # 5
Q["z_base0"] = Q["z_hs0"] + Q["fin_h"]              # 30
Q["z_ssr0"] = Q["z_base0"] + Q["base_t"]            # 34
Q["lid_in"] = Q["z_ssr0"] + Q["ssr_h"] + Q["cover_gap"]   # 67
Q["depth"] = Q["lid_in"] + Q["lid_t"]               # 69.5
Q["y_hs0"] = Q["y_pow0"] + Q["strip_bottom"]        # 134
Q["y_hs1"] = Q["y_hs0"] + Q["hs_h"]                 # 234
Q["cluster_y"] = Q["wall"] + Q["h_selv"] / 2        # 56
Q["pcb_z"] = Q["floor"] + Q["standoff"]
FRONT = dict(oled1=(-17.0, 28.0), oled2=(17.0, 28.0), pot=(0.0, 0.0), node=(0.0, -34.0))

# ---------------- rendijas (rectángulos u0,u1,v0,v1) y áreas libres
def cols(x0, x1, pitch=Q["pitch"], w=Q["slot"]):
    n = int((x1 - x0) // pitch) + 1
    return [(x0 + i * pitch - w / 2, x0 + i * pitch + w / 2) for i in range(n)]


VENTS = dict(
    # pared superior (plano XZ): u = x, v = z
    top=[(a, b, 8.0, 60.0) for a, b in cols(-78, 78)],
    # tapa de potencia (plano XY): u = x, v = y
    cover_out=[(a, b, 236.0, 246.0) for a, b in cols(-78, 78)],
    cover_in=[(a, b, 114.0, 132.0) for a, b in cols(-78, 78)],
    # paredes laterales de potencia (plano YZ): u = z, v = y
    side_pow=[(a, b, 114.0, 132.0) for a, b in cols(10, 66)],
    # SELV/DHT: pared inferior (plano XZ) y lateral derecha
    bottom_dht=[(a, b, 8.0, 40.0) for a, b in cols(36, 80)],
    bottom_selv=[(a, b, 8.0, 40.0) for a, b in cols(-70, -35)],
    side_dht=[(a, b, 8.0, 40.0) for a, b in cols(10, 50)],
)


def area(lst, n=1):
    return n * sum((b - a) * (d - c) for a, b, c, d in lst) / 100.0   # cm²


AREAS = dict(
    salida=area(VENTS["top"]) + area(VENTS["cover_out"]),
    entrada=area(VENTS["cover_in"]) + area(VENTS["side_pow"], 2),
    dht=area(VENTS["bottom_dht"]) + area(VENTS["side_dht"]),
    selv=area(VENTS["bottom_selv"]),
)

# ---------------- piezas de PCB
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

# ---------------- SVG
S = 3.2


def r_(x, y, w, h, **a):
    at = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" {at}/>'


def t_(x, y, s, size=11, anchor="middle", fill="#222", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{s}</text>'


def dh(x1, x2, y, label):
    return (f'<g stroke="#b00" stroke-width="1"><line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>'
            f'<line x1="{x1}" y1="{y-4}" x2="{x1}" y2="{y+4}"/><line x1="{x2}" y1="{y-4}" x2="{x2}" y2="{y+4}"/></g>'
            + t_((x1 + x2) / 2, y - 4, label, 11, fill="#b00"))


def dv(x, y1, y2, label):
    return (f'<g stroke="#b00" stroke-width="1"><line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}"/>'
            f'<line x1="{x-4}" y1="{y1}" x2="{x+4}" y2="{y1}"/><line x1="{x-4}" y1="{y2}" x2="{x+4}" y2="{y2}"/></g>'
            f'<text transform="translate({x-6},{(y1+y2)/2}) rotate(-90)" font-size="11" text-anchor="middle" fill="#b00">{label}</text>')


def build_svg():
    W, H = 1700, 1500
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="DejaVu Sans, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         t_(30, 38, "Termostato ESP8266 v2 – SELV + 3 SSR con disipador + DHT (mm)", 22, "start", weight="bold"),
         t_(30, 60, "Medidas de SSR, disipador, DHT, NodeMCU y OLED SUPUESTAS (genéricas). Presentar las piezas reales antes de imprimir.", 12, "start", "#555")]
    Wo, Ho = Q["w_out"], Q["h_out"]

    def box_xy(ox, oy):            # (x centrado, y desde la base) -> px
        return lambda x, y: (ox + (x + Wo / 2) * S, oy + (Ho - y) * S)

    # ---- ① interior (sin tapas)
    ox, oy = 90, 110
    p = box_xy(ox, oy)
    o.append(t_(ox + Wo * S / 2, oy - 30, "① Interior (sin tapas) – alzado frontal", 14, weight="bold"))
    o.append(r_(ox, oy, Wo * S, Ho * S, fill="#e8eaee", stroke="#000", stroke_width=1.5))
    # compartimento SELV
    x, y = p(-Q["w_in"] / 2, Q["y_bar0"])
    o.append(r_(x, y, Q["w_in"] * S, Q["h_selv"] * S, fill="#dfe6df", stroke="#555"))
    x, y = p(-Q["w_in"] / 2, Q["y_pow1"])
    o.append(r_(x, y, Q["w_in"] * S, Q["h_pow"] * S, fill="#f3e2e2", stroke="#a33"))
    x, y = p(-Q["w_in"] / 2, Q["y_pow0"])
    o.append(r_(x, y - 3 * S * 0, Q["w_in"] * S, Q["bar"] * S, fill="#8c8c8c", stroke="#444"))
    o[-1] = o[-1]
    # PCB
    cx = Q["cluster_x"]
    x, y = p(cx - 50, Q["cluster_y"] + 50)
    o.append(r_(x, y, 100 * S, 100 * S, fill="#1f6b3a", stroke="#000"))
    for hx in (-45, 45):
        for hy in (-45, 45):
            px_, py_ = p(cx + hx, Q["cluster_y"] + hy)
            o.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="{1.5*S:.1f}" fill="#fff" stroke="#000"/>')
    o.append(t_(*p(cx, Q["cluster_y"] + 8), "PCB 100×100", 12, fill="#fff"))
    o.append(t_(*p(cx, Q["cluster_y"] - 4), "(componentes ver v1)", 10, fill="#cde"))
    # cámara DHT
    x0, x1, y0, y1 = Q["dht_box"]
    xa, ya = p(x0, y1)
    o.append(r_(xa, ya, (x1 - x0) * S, (y1 - y0) * S, fill="#e6f2ff", stroke="#06c", stroke_dasharray="5 3"))
    o.append(t_(*p((x0 + x1) / 2, (y0 + y1) / 2 + 3), "DHT22", 12, fill="#06c"))
    o.append(t_(*p((x0 + x1) / 2, (y0 + y1) / 2 - 8), "cámara ventilada", 9, fill="#06c"))
    # disipadores + SSR
    for i, xs in enumerate(Q["ssr_x"]):
        yc = (Q["y_hs0"] + Q["y_hs1"]) / 2
        xa, ya = p(xs - Q["hs_w"] / 2, Q["y_hs1"])
        o.append(r_(xa, ya, Q["hs_w"] * S, Q["hs_h"] * S, fill="#bfc5cc", stroke="#333"))
        for k in range(Q["n_fins"]):
            fx = xa + (k + 0.5) * Q["hs_w"] * S / Q["n_fins"]
            o.append(f'<line x1="{fx:.1f}" y1="{ya:.1f}" x2="{fx:.1f}" y2="{ya+Q["hs_h"]*S:.1f}" stroke="#8a9098" stroke-width="1"/>')
        xa, ya = p(xs - Q["ssr_w"] / 2, yc + Q["ssr_l"] / 2)
        o.append(r_(xa, ya, Q["ssr_w"] * S, Q["ssr_l"] * S, rx=3, fill="#2b2b2b", stroke="#000"))
        o.append(r_(xa + 6, ya + 22 * S / 2.2, Q["ssr_w"] * S - 12, 14 * S, fill="#c33", stroke="none"))
        o.append(t_(xa + Q["ssr_w"] * S / 2, ya + Q["ssr_l"] * S / 2 + 4, f"SSR {Q['ssr_names'][i]}", 10, fill="#fff"))
    # bornas de red y fusible (marcadores)
    xa, ya = p(-62, Q["y_pow0"] + 18)
    o.append(r_(xa, ya, 40 * S, 12 * S, fill="#4a8a3c", stroke="#222"))
    o.append(t_(xa + 20 * S, ya + 7 * S, "bornas red L/N + 3 cargas", 9, fill="#fff"))
    xa, ya = p(30, Q["y_pow0"] + 18)
    o.append(r_(xa, ya, 34 * S, 12 * S, fill="#d8c070", stroke="#222"))
    o.append(t_(xa + 17 * S, ya + 7 * S, "fusible + TMOV", 9, fill="#222"))
    # flechas de aire
    for xs in (-78, -26, 26, 78):
        a1 = p(xs, Q["y_pow0"] + 4); a2 = p(xs, Q["y_pow0"] + 18)
        o.append(f'<line x1="{a1[0]:.1f}" y1="{a1[1]:.1f}" x2="{a2[0]:.1f}" y2="{a2[1]:.1f}" stroke="#06c" stroke-width="2" marker-end="url(#ar)"/>')
        b1 = p(xs, Q["y_hs1"] - 2); b2 = p(xs, Q["y_pow1"] - 2)
        o.append(f'<line x1="{b1[0]:.1f}" y1="{b1[1]:.1f}" x2="{b2[0]:.1f}" y2="{b2[1]:.1f}" stroke="#d33" stroke-width="2" marker-end="url(#ar2)"/>')
    o.insert(2, '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#06c"/></marker>'
                '<marker id="ar2" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#d33"/></marker></defs>')
    o.append(t_(*p(-Q["w_in"] / 2 + 3, Q["y_pow1"] - 8), "ZONA 230 V (cubierta fija, barrera ≥ 8 mm)", 10, "start", "#a33", "bold"))
    o.append(t_(*p(24, Q["y_bar0"] - 6), "ZONA SELV (5 V / 3,3 V)", 10, "start", "#254", "bold"))
    o.append(dh(ox, ox + Wo * S, oy + Ho * S + 22, f"{Wo:.0f}"))
    o.append(dv(ox - 20, oy, oy + Ho * S, f"{Ho:.0f}"))
    xa, _ = p(-Q["ssr_x"][0] * -1 - Q["hs_w"] / 2, 0)
    o.append(dh(*(p(Q["ssr_x"][1] - Q["hs_w"] / 2, 0)[0], p(Q["ssr_x"][1] + Q["hs_w"] / 2, 0)[0]), oy + Ho * S + 46, f"disipador {Q['hs_w']:.0f}"))
    o.append(dv(ox + Wo * S + 22, p(0, Q["y_hs1"])[1], p(0, Q["y_hs0"])[1], f"{Q['hs_h']:.0f}"))
    o.append(t_(ox + Wo * S / 2, oy + Ho * S + 74, "Azul: aire frío (entrada) · Rojo: aire caliente (salida, tiro natural)", 11, fill="#444"))

    # ---- ② tapas frontales
    fx = 700
    pf = box_xy(fx, oy)
    o.append(t_(fx + Wo * S / 2, oy - 30, "② Frontal con tapas (rendijas)", 14, weight="bold"))
    o.append(r_(fx, oy, Wo * S, Ho * S, rx=5, fill="#d6d9de", stroke="#000", stroke_width=1.5))
    x, y = pf(-Q["w_out"] / 2, Q["y_pow0"])
    o.append(r_(x, y, Wo * S, 1.5, fill="#555"))
    for a, b, c, d in VENTS["cover_out"] + VENTS["cover_in"]:
        xa, ya = pf(a, d)
        o.append(r_(xa, ya, (b - a) * S, (d - c) * S, fill="#222"))
    cxp, cyp = Q["cluster_x"], Q["cluster_y"]
    for k in ("oled1", "oled2"):
        xa, ya = pf(cxp + FRONT[k][0] - Q["win_w"] / 2, cyp + FRONT[k][1] + 3 + Q["win_h"] / 2)
        o.append(r_(xa, ya, Q["win_w"] * S, Q["win_h"] * S, fill="#111"))
    px_, py_ = pf(cxp, cyp)
    o.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="{Q["knob_d"]/2*S:.1f}" fill="#555" stroke="#222"/>')
    o.append(t_(fx + Wo * S / 2, oy + Ho * S + 22, "Salida arriba (23×10 ranuras) · entrada abajo (23×18)", 11, fill="#444"))

    # ---- ③ sección lateral
    sx, sy = 70, 1090
    zs = 5.2
    top_ = sy
    Hs = Ho * 1.25
    sc = 1.25

    def yz(z0, z1, y0, y1, fill, stroke="#333"):
        o.append(r_(sx + z0 * zs, top_ + (Ho - y1) * sc, (z1 - z0) * zs, (y1 - y0) * sc, fill=fill, stroke=stroke))

    o.append(t_(sx + 180, sy - 28, "③ Sección lateral (pared a la izquierda)", 14, weight="bold"))
    yz(0, Q["wall"], 0, Ho, "#bbb")
    yz(0, Q["lid_in"], Ho - Q["wall"], Ho, "#bbb")
    yz(0, Q["lid_in"], 0, Q["wall"], "#bbb")
    yz(Q["lid_in"], Q["depth"], 0, Ho, "#aaa")
    yz(0, Q["lid_in"], Q["y_bar0"], Q["y_pow0"], "#777")
    for xs in (0,):
        yz(Q["z_hs0"], Q["z_base0"], Q["y_hs0"], Q["y_hs1"], "#b9bfc7")
        yz(Q["z_base0"], Q["z_ssr0"], Q["y_hs0"], Q["y_hs1"], "#8a9098")
        yz(Q["z_ssr0"], Q["z_ssr0"] + Q["ssr_h"], (Q["y_hs0"] + Q["y_hs1"]) / 2 - Q["ssr_l"] / 2, (Q["y_hs0"] + Q["y_hs1"]) / 2 + Q["ssr_l"] / 2, "#2b2b2b")
    yz(Q["pcb_z"], Q["pcb_z"] + Q["pcb_t"], Q["cluster_y"] - 50, Q["cluster_y"] + 50, "#1f6b3a")
    yz(Q["pcb_z"] + Q["pcb_t"], Q["pcb_z"] + Q["pcb_t"] + Q["zone"], Q["cluster_y"] - 50, Q["cluster_y"] + 50, "#9fd4ad")
    yz(Q["lid_in"] - Q["node_h"], Q["lid_in"], Q["cluster_y"] - 34 - Q["node_w"] / 2, Q["cluster_y"] - 34 + Q["node_w"] / 2, "#4a7bd0")
    yz(Q["depth"], Q["depth"] + Q["knob_h"], Q["cluster_y"] - 10, Q["cluster_y"] + 10, "#444")
    o.append(dh(sx, sx + Q["depth"] * zs, top_ + Ho * sc + 30, f"profundidad {Q['depth']:.1f}"))
    o.append(dh(sx + Q["z_hs0"] * zs, sx + Q["z_base0"] * zs, top_ + Ho * sc + 60, f"aletas {Q['fin_h']:.0f}"))
    o.append(dh(sx + Q["z_base0"] * zs, sx + (Q["z_ssr0"] + Q["ssr_h"]) * zs, top_ + Ho * sc + 90, f"base {Q['base_t']:.0f} + SSR {Q['ssr_h']:.0f}"))
    o.append(dh(sx + (Q["z_ssr0"] + Q["ssr_h"]) * zs, sx + Q["lid_in"] * zs, top_ + Ho * sc + 120, f"cubrebornes {Q['cover_gap']:.0f}"))

    # ---- tabla
    tx, ty = 760, 1090
    rows = [
        ("Caja exterior", f"{Wo:.0f} × {Ho:.0f} × {Q['depth']:.1f} mm (+{Q['knob_h']:.0f} mando)"),
        ("Compartimento SELV", f"{Q['w_in']:.0f} × {Q['h_selv']:.0f} mm interior (abajo)"),
        ("Compartimento 230 V", f"{Q['w_in']:.0f} × {Q['h_pow']:.0f} mm interior (arriba), tapa propia"),
        ("Barrera entre ambos", f"{Q['bar']:.0f} mm + paso de mazo 5 V (3 pares)"),
        ("SSR ×3 (supuesto)", f"{Q['ssr_l']:.0f} × {Q['ssr_w']:.0f} × {Q['ssr_h']:.0f} mm (tipo SSR-40DA)"),
        ("Disipador ×3 (supuesto)", f"{Q['hs_w']:.0f} × {Q['hs_h']:.0f} mm, aletas {Q['fin_h']:.0f} mm verticales"),
        ("Rendijas salida", f"{AREAS['salida']:.0f} cm² libres (techo + tapa alta)"),
        ("Rendijas entrada", f"{AREAS['entrada']:.0f} cm² libres (tapa baja + 2 laterales)"),
        ("Cámara DHT", f"{AREAS['dht']:.0f} cm² de ventilación propia; aislada de la PCB"),
    ]
    o.append(t_(tx, ty - 30, "Cotas y ventilación", 14, "start", weight="bold"))
    for i, (a, b) in enumerate(rows):
        yy = ty + i * 28
        o.append(r_(tx, yy - 16, 900, 26, fill="#f6f6f6" if i % 2 == 0 else "#fff", stroke="none"))
        o.append(t_(tx + 8, yy + 2, a, 12, "start", weight="bold"))
        o.append(t_(tx + 230, yy + 2, b, 12, "start"))
    o.append("</svg>")
    return "\n".join(o)


(HERE / "esquema_v2.svg").write_text(build_svg(), encoding="utf-8")
SCENE = json.dumps(dict(Q=Q, FRONT=FRONT, VENTS=VENTS, AREAS=AREAS, parts=PCB_PARTS))
tpl = (HERE / "render_v2.template.html").read_text(encoding="utf-8")
(HERE / "render_v2.html").write_text(tpl.replace("__SCENE__", SCENE), encoding="utf-8")
print("ok", Q["w_out"], Q["h_out"], Q["depth"], {k: round(v, 1) for k, v in AREAS.items()})
