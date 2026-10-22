#!/usr/bin/env python3
"""Genera esquema_medidas.svg y render_3d.html de la caja del termostato.

Todas las cotas están en mm y se editan en PARAMS. Las posiciones de la PCB salen
de pcbway/thermostat_universal_rev_a/jlcpcb/CPL_JLCPCB.csv (origen abajo-izquierda,
Y hacia arriba). Las medidas de NodeMCU, OLED y potenciómetro son SUPUESTAS
(módulos genéricos): sustituirlas por las medidas con calibre.
"""
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CPL = HERE.parent / "pcbway/thermostat_universal_rev_a/jlcpcb/CPL_JLCPCB.csv"

P = dict(
    pcb=100.0, pcb_t=1.6, hole_off=5.0, hole_d=3.0,
    wall=3.0, clear=3.0,                 # pared y holgura PCB-pared
    floor=3.0, standoff=6.0,             # suelo y separadores
    zone=14.0,                           # altura útil sobre la PCB (condensador 11 + holgura/mazos)
    node_l=58.0, node_w=31.0, node_h=13.0,   # NodeMCU LoLin V3 con pines hacia atrás
    oled_w=27.3, oled_h=27.8, oled_t=4.0,    # SSD1306 0,96" 4 pines
    win_w=24.0, win_h=13.0,              # ventana de cada OLED
    pot_body=16.0, pot_len=10.0, pot_hole=7.0, knob_d=20.0, knob_h=15.0,
    lid=2.5,
)
P["inner"] = P["pcb"] + 2 * P["clear"]            # 106
P["outer"] = P["inner"] + 2 * P["wall"]           # 112
P["pcb_z"] = P["floor"] + P["standoff"]           # cara inferior PCB
P["zone_top"] = P["pcb_z"] + P["pcb_t"] + P["zone"]
P["lid_in"] = P["zone_top"] + P["node_h"] + 1.0   # cara interior de la tapa
P["depth"] = P["lid_in"] + P["lid"]               # profundidad total de la caja

# Posiciones (centro en coordenadas relativas al centro de la tapa; y hacia arriba)
FRONT = dict(
    oled1=(-17.0, 28.0), oled2=(17.0, 28.0), pot=(0.0, 0.0), node=(0.0, -34.0),
)

parts = []
with open(CPL, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        d = r["Designator"]
        x = float(r["Mid X"].replace("mm", ""))
        y = float(r["Mid Y"].replace("mm", ""))
        parts.append((d, x, y))
POS = {d: (x, y) for d, x, y in parts}

JST_PINS = dict(J1=3, J8=3, J9=3, J2=4, J3=4, J4=4, J5=4, J6=4, J7=4, J10=5)


def kind(d):
    if d in JST_PINS:
        return dict(t="jst", n=JST_PINS[d])
    if d in ("J11", "J12", "J13"):
        return dict(t="phoenix")
    if d.startswith("R"):
        return dict(t="res")
    if d in ("C8", "C10"):
        return dict(t="elec")
    if d.startswith("C"):
        return dict(t="cer")
    if d.startswith("Q"):
        return dict(t="to92")
    if d == "F1":
        return dict(t="ptc")
    raise ValueError(d)


PCB_PARTS = [dict(ref=d, x=x, y=y, **kind(d)) for d, x, y in parts]

# ---------------------------------------------------------------- SVG
S = 4.2  # px por mm en vistas 2D


def svg_rect(x, y, w, h, **a):
    at = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" {at}/>'


def svg_text(x, y, t, size=11, anchor="middle", fill="#222", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{fill}" font-weight="{weight}">{t}</text>')


def dim_h(x1, x2, y, label, off=10):
    return (f'<g stroke="#b00" fill="none" stroke-width="1"><line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>'
            f'<line x1="{x1}" y1="{y-4}" x2="{x1}" y2="{y+4}"/><line x1="{x2}" y1="{y-4}" x2="{x2}" y2="{y+4}"/></g>'
            + svg_text((x1 + x2) / 2, y - 4, label, 11, fill="#b00"))


def dim_v(x, y1, y2, label):
    return (f'<g stroke="#b00" fill="none" stroke-width="1"><line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}"/>'
            f'<line x1="{x-4}" y1="{y1}" x2="{x+4}" y2="{y1}"/><line x1="{x-4}" y1="{y2}" x2="{x+4}" y2="{y2}"/></g>'
            f'<text transform="translate({x-6},{(y1+y2)/2}) rotate(-90)" font-size="11" text-anchor="middle" fill="#b00">{label}</text>')


def build_svg():
    out = []
    W, H = 1500, 1260
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
               'font-family="DejaVu Sans, Arial, sans-serif">')
    out.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    out.append(svg_text(30, 38, "Termostato ESP8266 – esquema con medidas (mm)", 22, "start", weight="bold"))
    out.append(svg_text(30, 60, "PCB Rev A 100×100 + NodeMCU + 2 OLED + potenciómetro. Medidas de módulos SUPUESTAS: verificar con calibre.", 12, "start", "#555"))

    # ---- Vista 1: PCB (planta, vista desde arriba)
    ox, oy = 70, 110      # origen px de la esquina sup-izq de la PCB
    pcb = P["pcb"] * S
    out.append(svg_text(ox + pcb / 2, oy - 28, "① PCB – vista superior (componentes)", 14, weight="bold"))
    out.append(svg_rect(ox, oy, pcb, pcb, fill="#1f6b3a", stroke="#000", stroke_width=1.5))

    def px(x, y):
        return ox + x * S, oy + (P["pcb"] - y) * S

    for hx in (P["hole_off"], P["pcb"] - P["hole_off"]):
        for hy in (P["hole_off"], P["pcb"] - P["hole_off"]):
            cx, cy = px(hx, hy)
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{P["hole_d"]/2*S:.1f}" fill="#fff" stroke="#000"/>')
    for p in PCB_PARTS:
        cx, cy = px(p["x"], p["y"])
        if p["t"] == "jst":
            w, h = ((p["n"] - 1) * 2.5 + 4.9) * S, 5.75 * S
            out.append(svg_rect(cx - w / 2, cy - h / 2, w, h, fill="#f4f0e6", stroke="#333"))
        elif p["t"] == "phoenix":
            w, h = 10.16 * S, 9.8 * S
            out.append(svg_rect(cx - w / 2, cy - h / 2, w, h, fill="#2d8f4e", stroke="#000"))
            out.append(f'<polygon points="{cx+w/2:.1f},{cy-h/3:.1f} {cx+w/2+8:.1f},{cy:.1f} {cx+w/2:.1f},{cy+h/3:.1f}" fill="#fc0"/>')
        elif p["t"] == "res":
            out.append(svg_rect(cx - 3.15 * S, cy - 1.15 * S, 6.3 * S, 2.3 * S, rx=3, fill="#d9b97a", stroke="#533"))
        elif p["t"] == "elec":
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{2.5*S:.1f}" fill="#222" stroke="#000"/>')
        elif p["t"] == "cer":
            out.append(svg_rect(cx - 2.5 * S, cy - 1.2 * S, 5 * S, 2.4 * S, fill="#e0a020", stroke="#333"))
        elif p["t"] == "to92":
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{2.4*S:.1f}" fill="#222" stroke="#000"/>')
        elif p["t"] == "ptc":
            out.append(svg_rect(cx - 3.7 * S, cy - 1.9 * S, 7.4 * S, 3.8 * S, fill="#e8d34a", stroke="#333"))
        if p["t"] in ("jst", "phoenix", "to92", "ptc", "elec") or p["ref"] in ("R1", "R2", "R5", "R10"):
            out.append(svg_text(cx, cy + 3, p["ref"], 9, fill="#000" if p["t"] in ("jst", "ptc") else "#fff"))
    out.append(dim_h(ox, ox + pcb, oy + pcb + 24, "100,0"))
    out.append(dim_v(ox - 22, oy, oy + pcb, "100,0"))
    a = P["hole_off"] * S
    out.append(dim_h(ox + a, ox + pcb - a, oy + pcb + 50, "90,0 (centros taladros M3 Ø3,0)"))
    out.append(svg_text(ox + pcb / 2, oy + pcb + 75, "J11–J13: bornas Phoenix 10,16×9,8 (entrada de cable: confirmar lado)", 10, fill="#555"))

    # ---- Vista 2: frontal de la tapa
    fx, fy = 600, 110
    L = P["outer"] * S
    out.append(svg_text(fx + L / 2, fy - 28, "② Tapa frontal (cara exterior)", 14, weight="bold"))
    out.append(svg_rect(fx, fy, L, L, rx=6, fill="#e9e9e9", stroke="#000", stroke_width=1.5))

    def fp(x, y):
        return fx + L / 2 + x * S, fy + L / 2 - y * S

    for k in ("oled1", "oled2"):
        cx, cy = fp(*FRONT[k])
        cy_win = cy - 3.0 * S   # el área activa está ~3 mm por encima del centro del módulo
        out.append(svg_rect(cx - P["oled_w"] / 2 * S, cy - P["oled_h"] / 2 * S, P["oled_w"] * S, P["oled_h"] * S,
                            fill="none", stroke="#999", stroke_dasharray="4 3"))
        out.append(svg_rect(cx - P["win_w"] / 2 * S, cy_win - P["win_h"] / 2 * S, P["win_w"] * S, P["win_h"] * S,
                            fill="#111", stroke="#000"))
    cx, cy = fp(*FRONT["pot"])
    out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{P["knob_d"]/2*S:.1f}" fill="#bbb" stroke="#333"/>')
    out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{P["pot_hole"]/2*S:.1f}" fill="#555"/>')
    nx, ny = fp(*FRONT["node"])
    out.append(svg_rect(nx - P["node_l"] / 2 * S, ny - P["node_w"] / 2 * S, P["node_l"] * S, P["node_w"] * S,
                        fill="none", stroke="#06c", stroke_dasharray="6 4"))
    out.append(svg_text(nx, ny + 4, "NodeMCU detrás (no visible)", 10, fill="#06c"))
    o1 = fp(*FRONT["oled1"]); o2 = fp(*FRONT["oled2"])
    out.append(dim_h(o1[0] - P["oled_w"] / 2 * S, o1[0] + P["oled_w"] / 2 * S, fy + 24, "27,3"))
    out.append(dim_h(o1[0] + P["oled_w"] / 2 * S, o2[0] - P["oled_w"] / 2 * S + 0.01, fy + 44, "6"))
    out.append(dim_h(fx, fx + L, fy + L + 24, f"{P['outer']:.0f}"))
    out.append(dim_v(fx - 22, fy, fy + L, f"{P['outer']:.0f}"))
    out.append(svg_text(cx, cy + P["knob_d"] / 2 * S + 16, f"Pot: taladro Ø{P['pot_hole']:.0f}, mando Ø{P['knob_d']:.0f}", 10, fill="#333"))
    out.append(svg_text(o1[0], fy + 4 * S + 3 + 0, "", 10))
    out.append(svg_text(fx + L / 2, fy + L + 52, f"Ventana OLED {P['win_w']:.0f}×{P['win_h']:.0f} (área activa 21,7×10,9)", 10, fill="#555"))

    # ---- Vista 3: sección lateral (pila en Z)
    sx, sy = 70, 720
    D = P["depth"] * S
    out.append(svg_text(sx + 250, sy - 38, "③ Sección lateral – pila de capas (pared a la izquierda)", 14, weight="bold"))
    base_y = sy + 100

    # En la sección el eje horizontal es Z (profundidad) y el vertical es el ancho
    zs = 1.9 * S
    H1 = P["outer"] * 1.9
    top = sy
    cy_mid = top + H1 / 2

    def zbox(z0, z1, y0, y1, fill, stroke="#333", op=1.0):
        out.append(svg_rect(sx + z0 * zs, top + (P["outer"] / 2 - y1) * 1.9 * (1), (z1 - z0) * zs,
                            (y1 - y0) * 1.9, fill=fill, stroke=stroke, opacity=op))

    # caja
    zbox(0, P["floor"], -P["outer"] / 2, P["outer"] / 2, "#cfcfcf")
    zbox(0, P["lid_in"], P["inner"] / 2, P["outer"] / 2, "#cfcfcf")
    zbox(0, P["lid_in"], -P["outer"] / 2, -P["inner"] / 2, "#cfcfcf")
    zbox(P["lid_in"], P["depth"], -P["outer"] / 2, P["outer"] / 2, "#b9b9b9")
    # separadores y PCB
    for yy in (-45, 45):
        zbox(P["floor"], P["pcb_z"], yy - 2.5, yy + 2.5, "#e0b050")
    zbox(P["pcb_z"], P["pcb_z"] + P["pcb_t"], -50, 50, "#1f6b3a")
    zbox(P["pcb_z"] + P["pcb_t"], P["zone_top"], -50, 50, "#9fd4ad", op=0.55)
    # NodeMCU + OLED + pot
    zbox(P["lid_in"] - P["node_h"], P["lid_in"], FRONT["node"][1] - P["node_w"] / 2, FRONT["node"][1] + P["node_w"] / 2, "#4a7bd0")
    for k in ("oled1",):
        zbox(P["lid_in"] - P["oled_t"], P["lid_in"], FRONT[k][1] - P["oled_h"] / 2, FRONT[k][1] + P["oled_h"] / 2, "#222")
    zbox(P["lid_in"] - P["pot_len"], P["lid_in"], -P["pot_body"] / 2, P["pot_body"] / 2, "#888")
    zbox(P["depth"], P["depth"] + P["knob_h"], -P["knob_d"] / 2, P["knob_d"] / 2, "#444")

    def xz(z):
        return sx + z * zs

    bot = top + H1 + 28
    lab = [(0, P["floor"], "suelo 3"), (P["floor"], P["pcb_z"], "sep. 6"), (P["pcb_z"], P["pcb_z"] + P["pcb_t"], "PCB 1,6"),
           (P["pcb_z"] + P["pcb_t"], P["zone_top"], f"comp.+mazos {P['zone']:.0f}"),
           (P["zone_top"], P["lid_in"], f"NodeMCU {P['node_h']:.0f}+1"), (P["lid_in"], P["depth"], "tapa 2,5")]
    for i, (z0, z1, t) in enumerate(lab):
        out.append(dim_h(xz(z0), xz(z1), bot + 22 * (i % 2) + 8, f"{z1-z0:.1f}".replace(".0", "")))
        out.append(svg_text((xz(z0) + xz(z1)) / 2, bot + 22 * (i % 2) + 30 + 0, t, 9, fill="#555"))
    out.append(dim_h(xz(0), xz(P["depth"]), bot + 80, f"profundidad caja {P['depth']:.1f}"))
    out.append(dim_h(xz(P["depth"]), xz(P["depth"] + P["knob_h"]), bot + 110, f"mando +{P['knob_h']:.0f}"))
    out.append(svg_text(xz(0), top - 8, "pared", 10, "start", "#555"))
    out.append(svg_text(xz(P["depth"] + P["knob_h"]), top - 8, "frente", 10, "end", "#555"))

    # ---- Tabla de medidas
    tx, ty = 900, 720
    rows = [
        ("Caja exterior", f"{P['outer']:.0f} × {P['outer']:.0f} × {P['depth']:.1f} mm (+{P['knob_h']:.0f} del mando)"),
        ("Interior", f"{P['inner']:.0f} × {P['inner']:.0f} mm; pared {P['wall']:.0f}"),
        ("PCB", "100 × 100 × 1,6; taladros Ø3,0 a 5 mm del borde"),
        ("Separadores", f"{P['standoff']:.0f} mm, M3 (usar Ø3,2 en la caja)"),
        ("Altura sobre PCB", f"{P['zone']:.0f} mm (condensador 11 + mazos JST)"),
        ("NodeMCU (supuesto)", f"{P['node_l']:.0f} × {P['node_w']:.0f}, alto {P['node_h']:.0f} con pines"),
        ("OLED ×2 (supuesto)", f"{P['oled_w']} × {P['oled_h']} × {P['oled_t']}; ventana {P['win_w']:.0f}×{P['win_h']:.0f}"),
        ("Potenciómetro", f"cuerpo Ø{P['pot_body']:.0f}×{P['pot_len']:.0f}; taladro Ø{P['pot_hole']:.0f}; mando Ø{P['knob_d']:.0f}"),
        ("Acceso USB", "abertura lateral izquierda ~12×8 mm"),
    ]
    out.append(svg_text(tx, ty - 38, "Cotas principales", 14, "start", weight="bold"))
    for i, (a_, b_) in enumerate(rows):
        yy = ty + i * 28
        out.append(svg_rect(tx, yy - 16, 560, 26, fill="#f6f6f6" if i % 2 == 0 else "#fff", stroke="none"))
        out.append(svg_text(tx + 8, yy + 2, a_, 12, "start", weight="bold"))
        out.append(svg_text(tx + 190, yy + 2, b_, 12, "start"))
    out.append("</svg>")
    return "\n".join(out)


(HERE / "esquema_medidas.svg").write_text(build_svg(), encoding="utf-8")

# ---------------------------------------------------------------- HTML 3D
SCENE = json.dumps(dict(P=P, FRONT=FRONT, parts=PCB_PARTS))
TEMPLATE = (HERE / "render_3d.template.html").read_text(encoding="utf-8")
(HERE / "render_3d.html").write_text(TEMPLATE.replace("__SCENE__", SCENE), encoding="utf-8")
print("ok", P["outer"], P["depth"])
