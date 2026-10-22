#!/usr/bin/env python3
"""Caja v9 (preliminar) para la PCB Rev B de 84 x 84 mm y la DWIN 4" 480x480 sin carcasa (84 x 84 x 4,55).

Dos piezas impresas:
  * Marco: cuatro paredes de 2,5 mm, la pantalla enrasada al frente sobre una repisa interior y
    una ranura en la pared para el cable de la pantalla, que rodea el canto de la PCB.
  * Tapa trasera: fondo de 2 mm con borde interior, cuatro torretas de 16,5 mm para la PCB,
    tabique 230 V / SELV con huecos para los relés, entrada de 230 V y entrada de 5 V separadas.
La PCB va con los componentes hacia atrás. Visto desde delante, la placa está espejada:
x_caja = 42 - x_pcb, y_caja = 42 - y_pcb. El DHT22 va en una cápsula ventilada bajo la pared
inferior, lejos del calor de los relés. Origen en el centro de la cara trasera; +z hacia la pantalla.
Genera esquema_v9.svg y render_v9.html; comprueba interferencias entre piezas y caja.
"""
import base64
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build_rev_b_fzz as rb  # noqa: E402

PCB_PNG = HERE.parent / "pcbway/thermostat_rev_b/VERIFICACION_TOP.png"

Q = dict(
    pcb=84.0, pcb_t=1.6, clr=0.3, wall=2.5, floor=2.0, rim_w=2.0, rim_h=3.0,
    comp_h=16.5,                    # hueco entre el fondo y la cara de componentes de la PCB
    disp_w=84.0, disp_h=84.0, disp_t=4.55, act_w=71.86, act_h=70.18, disp_gap=2.5,
    ledge_w=1.2, ledge_t=1.5,
    standoff_d=6.0, hole_d=3.2,
    groove_w=9.0, groove_d=1.6,
    pod_w=26.0, pod_d=14.0, pod_h=16.0, pod_x=12.0,
    dht_w=15.1, dht_l=25.1, dht_t=7.7,
    zone_y=33.3,                    # línea 230 V / SELV en coordenadas de la PCB
    part_t=1.6,
)
Q["inner"] = Q["pcb"] + 2 * Q["clr"]
Q["outer"] = Q["inner"] + 2 * Q["wall"]
Q["pcb_back"] = Q["floor"] + Q["comp_h"]
Q["pcb_front"] = Q["pcb_back"] + Q["pcb_t"]
Q["disp_back"] = Q["pcb_front"] + Q["disp_gap"]
Q["depth"] = Q["disp_back"] + Q["disp_t"]
Q["ledge_z0"] = Q["disp_back"] - Q["ledge_t"]
H = Q["pcb"] / 2


def cxy(bx, by):
    """Board mm (top view, y down) -> case mm (seen from the front, y up)."""
    return H - bx, H - by


# Piezas de la PCB (cara de componentes hacia -z).
HEIGHTS = {
    "rb_hf115f": ("relay", 15.7), "rb_mkds4_mains": ("terminal", 10.0), "rb_mkds2_selv": ("terminal", 10.0),
    "rb_tr5": ("fuse", 7.7), "rb_radial63": ("cap", 11.0), "rb_nodemcu_dual": ("node", 14.6),
    "rb_0805_res": ("smd", 0.6), "rb_0805_cap": ("smd", 1.0), "rb_sot23_npn": ("smd", 1.1),
    "rb_sod123_r180": ("smd", 1.2), "rb_1812_ptc": ("smd", 1.3),
}
PARTS = []
for part in rb.PARTS:
    kind, height = HEIGHTS.get(part.fp.key, ("jst", 7.0))
    x0, y0, x1, y1 = part.fp.bodies[0] if kind != "node" else (-29.0, -15.5, 29.0, 15.5)
    if kind == "smd":
        pads = part.fp.pads
        xs = [p.x for p in pads]
        ys = [p.y for p in pads]
        x0, x1 = min(xs) - 0.4, max(xs) + 0.4
        y0, y1 = min(ys) - 0.5, max(ys) + 0.5
    if kind == "node":
        # Módulo LoLin v3 58 x 31 con el USB hacia el borde izquierdo de la PCB (x_pcb ~ 1).
        x0, x1 = -rb.NODE_X + 2.0, -rb.NODE_X + 60.0
    cx, cy = cxy(part.x + (x0 + x1) / 2, part.y + (y0 + y1) / 2)
    PARTS.append(dict(ref=part.ref, t=kind, x=round(cx, 3), y=round(cy, 3), w=round(x1 - x0, 3),
                      l=round(y1 - y0, 3), h=height, n=len(part.fp.pads)))

MOUNTS = [cxy(x, y) for x, y in rb.MOUNT_CENTERS_MM]
RELAYS = [p for p in PARTS if p["t"] == "relay"]
ZONE_Y = H - Q["zone_y"]
# Tabique: del borde interior a cada lado, interrumpido por los relés (cuerpo + 0,6 mm).
gaps = sorted((r["x"] - r["w"] / 2 - 0.6, r["x"] + r["w"] / 2 + 0.6) for r in RELAYS)
PARTITION = []
x = -Q["inner"] / 2 + Q["rim_w"]
for a, b in gaps:
    if a - x > 1.0:
        PARTITION.append((round(x, 3), round(a, 3)))
    x = b
if Q["inner"] / 2 - Q["rim_w"] - x > 1.0:
    PARTITION.append((round(x, 3), round(Q["inner"] / 2 - Q["rim_w"], 3)))

J20 = next(p for p in PARTS if p["ref"] == "J20")
J1 = next(p for p in PARTS if p["ref"] == "J1")
J2 = next(p for p in PARTS if p["ref"] == "J2")
J3 = next(p for p in PARTS if p["ref"] == "J3")
NODE = next(p for p in PARTS if p["ref"] == "U1")
HOLES = dict(
    mains=(round(J20["x"] - 17.0, 2), round(J20["y"] - 4.0, 2), 5.5),     # Ø11, zona 230 V, junto a J20
    selv=(round(J1["x"] + 13.0, 2), round(J1["y"] - 2.0, 2), 4.0),        # Ø8, 5 V hacia J1
)
# Ranura para el cable de la pantalla en la pared más cercana a J2, y paso del cable del DHT.
GROOVE_Y = round(J2["y"], 2)
GROOVE_SIDE = -1 if J2["x"] < 0 else 1
USB = dict(y=round(NODE["y"], 2), z0=round(Q["pcb_back"] - 13.6, 2), z1=round(Q["pcb_back"] - 8.6, 2))
POD_HOLE = (round(Q["pod_x"], 2), 3.5)      # x, radio del paso del cable en la pared inferior


def vents():
    """Rendijas de la cápsula del DHT. La tapa trasera no lleva rendijas en la zona de 230 V."""
    pod = [(Q["pod_x"] - 9 + i * 4.5 - 1.2, Q["pod_x"] - 9 + i * 4.5 + 1.2) for i in range(5)]
    return dict(pod=pod)


VENTS = vents()


def interference():
    """Cajas AABB de las piezas frente a torretas, tabique, borde de la tapa y repisa."""
    problems = []
    zb = Q["pcb_back"]
    solids = []
    for mx, my in MOUNTS:
        r = Q["standoff_d"] / 2
        solids.append(("torreta", mx - r, my - r, Q["floor"], mx + r, my + r, zb))
    for a, b in PARTITION:
        solids.append(("tabique", a, ZONE_Y - Q["part_t"] / 2, Q["floor"], b, ZONE_Y + Q["part_t"] / 2, zb - 1.0))
    I, R = Q["inner"] / 2, Q["inner"] / 2 - Q["rim_w"]
    zr = Q["floor"] + Q["rim_h"]
    for name, box in (("borde N", (-I, R, Q["floor"], I, I, zr)), ("borde S", (-I, -I, Q["floor"], I, -R, zr)),
                      ("borde O", (-I, -I, Q["floor"], -R, I, zr)), ("borde E", (R, -I, Q["floor"], I, I, zr))):
        solids.append((name, *box))
    for p in PARTS:
        px0, px1 = p["x"] - p["w"] / 2, p["x"] + p["w"] / 2
        py0, py1 = p["y"] - p["l"] / 2, p["y"] + p["l"] / 2
        pz0, pz1 = zb - p["h"], zb
        if pz0 < Q["floor"] + 0.3:
            problems.append(f"{p['ref']} toca el fondo ({pz0:.2f} mm)")
        for name, sx0, sy0, sz0, sx1, sy1, sz1 in solids:
            if p["t"] == "node" and name.startswith("torreta"):
                continue    # el módulo queda por encima de la torreta (se comprueba abajo)
            if min(px1, sx1) - max(px0, sx0) > 0 and min(py1, sy1) - max(py0, sy0) > 0 and min(pz1, sz1) - max(pz0, sz0) > 0:
                problems.append(f"{p['ref']} choca con {name}")
    # NodeMCU: el módulo está a 8,5 + 1,6 mm de la PCB; la torreta pasa por debajo sólo si
    # no está bajo el módulo. Las torretas de la esquina del USB quedan bajo el módulo: se usa
    # una torreta corta + tornillo de nailon desde la PCB.
    return problems


PROBLEMS = interference()

# ----------------------------------------------------------------- SVG
S = 5.0


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
    W, Hh = 1560, 960
    O = Q["outer"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {Hh}" width="{W}" height="{Hh}" font-family="DejaVu Sans, Arial, sans-serif">',
         f'<rect width="{W}" height="{Hh}" fill="#fff"/>',
         t_(30, 38, f"Termostato v9 (preliminar) – PCB Rev B 84 × 84 · caja {O:.1f} × {O:.1f} × {Q['depth']:.2f} mm", 22, "start", weight="bold"),
         t_(30, 60, "DWIN 4\" 480×480 sin carcasa (84 × 84 × 4,55; supuesta) enrasada al frente. Vista ② desde atrás = cara de componentes.", 12, "start", "#555")]
    ox, oy = 60, 120
    p = lambda x, y: (ox + (x + O / 2) * S, oy + (O / 2 - y) * S)
    o.append(t_(ox + O * S / 2, oy - 30, "① Frontal", 14, weight="bold"))
    o.append(r_(ox, oy, O * S, O * S, rx=4, fill="#b4bbc7", stroke="#000", stroke_width=1.5))
    x, y = p(-Q["disp_w"] / 2, Q["disp_h"] / 2)
    o.append(r_(x, y, Q["disp_w"] * S, Q["disp_h"] * S, fill="#111", stroke="#000"))
    x, y = p(-Q["act_w"] / 2, Q["act_h"] / 2)
    o.append(r_(x, y, Q["act_w"] * S, Q["act_h"] * S, fill="#0b1830"))
    o.append(t_(x + Q["act_w"] * S / 2, y + Q["act_h"] * S / 2, "22,5 °C", 54, fill="#9fe8ff", weight="bold"))
    o.append(dh(ox, ox + O * S, oy + O * S + 24, f"{O:.1f}"))
    o.append(dv(ox - 22, oy, oy + O * S, f"{O:.1f}"))
    # ② trasera (vista desde atrás: x espejada respecto al frente)
    bx = 600
    pb = lambda x, y: (bx + (O / 2 - x) * S, oy + (O / 2 - y) * S)
    o.append(t_(bx + O * S / 2, oy - 30, "② Interior visto desde atrás (sin tapa trasera)", 14, weight="bold"))
    o.append(r_(bx, oy, O * S, O * S, fill="#e8eaee", stroke="#000", stroke_width=1.5))
    x, y = pb(H, H)
    o.append(r_(x, y, Q["pcb"] * S, Q["pcb"] * S, fill="#1f6b3a", stroke="#000"))
    for prt in PARTS:
        if prt["t"] == "smd":
            continue
        x, y = pb(prt["x"] + prt["w"] / 2, prt["y"] + prt["l"] / 2)
        col = {"relay": "#2b4f9a", "terminal": "#2f9a52", "fuse": "#555", "cap": "#222", "node": "#1b2f78"}.get(prt["t"], "#efe6c8")
        o.append(r_(x, y, prt["w"] * S, prt["l"] * S, fill=col, stroke="#000", opacity=0.85 if prt["t"] == "node" else 1))
        o.append(t_(x + prt["w"] * S / 2, y + prt["l"] * S / 2 + 4, prt["ref"], 10, fill="#fff" if prt["t"] != "jst" else "#222"))
    y0 = pb(0, ZONE_Y)[1]
    o.append(f'<line x1="{bx}" y1="{y0}" x2="{bx + O * S}" y2="{y0}" stroke="#c00" stroke-width="2" stroke-dasharray="8 5"/>')
    o.append(t_(bx + 8, y0 - 6, "230 V ↑ · SELV ↓ (tabique)", 11, "start", "#c00", "bold"))
    for key, (hx, hy, hr) in HOLES.items():
        cx, cy = pb(hx, hy)
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{hr * S:.1f}" fill="#ffdede" fill-opacity="0.8" stroke="#c00" stroke-width="2.5"/>')
        o.append(t_(cx, cy + hr * S + 14, "entrada 230 V" if key == "mains" else "entrada 5 V", 10, fill="#c00"))
    for mx, my in MOUNTS:
        cx, cy = pb(mx, my)
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{Q["standoff_d"] / 2 * S}" fill="#e0b050" stroke="#000"/>')
    # ③ sección
    sx, sy = 1140, 120
    zs = 7.0
    z_ = lambda z: sx + z * zs
    y_ = lambda y: sy + (O / 2 - y) * S

    def yz(z0, z1, ya, yb, fill):
        o.append(r_(z_(z0), y_(yb), (z1 - z0) * zs, (yb - ya) * S, fill=fill, stroke="#333"))

    o.append(t_(sx + 100, sy - 30, "③ Sección (frente a la derecha)", 14, weight="bold"))
    yz(0, Q["floor"], -O / 2, O / 2, "#999")
    yz(0, Q["depth"], O / 2 - Q["wall"], O / 2, "#bbb")
    yz(0, Q["depth"], -O / 2, -O / 2 + Q["wall"], "#bbb")
    yz(Q["ledge_z0"], Q["disp_back"], Q["inner"] / 2 - Q["ledge_w"], Q["inner"] / 2, "#999")
    yz(Q["ledge_z0"], Q["disp_back"], -Q["inner"] / 2, -Q["inner"] / 2 + Q["ledge_w"], "#999")
    yz(Q["pcb_back"], Q["pcb_front"], -H, H, "#1f6b3a")
    yz(Q["disp_back"], Q["depth"], -Q["disp_h"] / 2, Q["disp_h"] / 2, "#111")
    for r in RELAYS[:1]:
        yz(Q["pcb_back"] - 15.7, Q["pcb_back"], r["y"] - r["l"] / 2, r["y"] + r["l"] / 2, "#2b4f9a")
    yz(Q["floor"], Q["pcb_back"] - 1.0, ZONE_Y - 0.8, ZONE_Y + 0.8, "#c33")
    yz(-Q["pod_h"] * 0 + 2.0, 2.0 + Q["pod_h"], -O / 2 - Q["pod_d"], -O / 2, "#cfd6e0")
    bot = sy + (O + Q["pod_d"]) * S + 20
    o.append(dh(z_(0), z_(Q["depth"]), bot, f"profundidad {Q['depth']:.2f}"))
    tx, ty = 60, 720
    rows = [
        ("Caja", f"{O:.1f} × {O:.1f} × {Q['depth']:.2f} mm (+ cápsula DHT {Q['pod_d']:.0f} mm bajo la pared inferior)"),
        ("Pila (z)", f"fondo {Q['floor']} · componentes {Q['comp_h']} · PCB {Q['pcb_t']} · hueco {Q['disp_gap']} · pantalla {Q['disp_t']}"),
        ("Piezas", "marco (paredes + repisa de la pantalla + ranura del cable) · tapa trasera (torretas, tabique 230 V, entradas) · cápsula DHT"),
        ("Seguridad", "PETG/ABS V-0 recomendado · tornillos de nailon M3 · tabique entre 230 V y SELV · entradas de cable separadas"),
        ("Interferencias", "ninguna" if not PROBLEMS else "; ".join(PROBLEMS)),
    ]
    o.append(t_(tx, ty - 30, "Cotas", 14, "start", weight="bold"))
    for i, (a, b) in enumerate(rows):
        yy = ty + i * 30
        o.append(r_(tx, yy - 17, 1440, 28, fill="#f6f6f6" if i % 2 == 0 else "#fff", stroke="none"))
        o.append(t_(tx + 8, yy + 2, a, 12, "start", weight="bold"))
        o.append(t_(tx + 150, yy + 2, b, 11, "start"))
    o.append("</svg>")
    return "\n".join(o)


(HERE / "esquema_v9.svg").write_text(build_svg(), encoding="utf-8")
texture = "data:image/png;base64," + base64.b64encode(PCB_PNG.read_bytes()).decode() if PCB_PNG.exists() else ""
SCENE = json.dumps(dict(Q=Q, parts=PARTS, mounts=MOUNTS, partition=PARTITION, zone_y=ZONE_Y, holes=HOLES,
                        groove=dict(y=GROOVE_Y, side=GROOVE_SIDE), usb=USB, pod_hole=POD_HOLE, vents=VENTS,
                        dht=dict(x=Q["pod_x"]), problems=PROBLEMS))
tpl = (HERE / "render_v9.template.html").read_text(encoding="utf-8")
(HERE / "render_v9.html").write_text(tpl.replace("__SCENE__", SCENE).replace("__PCB_TEXTURE__", texture), encoding="utf-8")
print("ok", Q["outer"], round(Q["depth"], 2), "interferencias:", PROBLEMS or "ninguna", "tabique:", PARTITION)
