# Termostato — Piezas, pedido PCBWay y software

Actualizado: 2026-09-10. Resuelve pending #1 (amperaje) y prepara el pedido.
Carga declarada por el usuario: **6 A inductivo / 3,5 A resistivo mínimo por canal**.

---

## 1. Decisión de SSR (resuelve pending #1)

> **Nota 2026-09-10 (3ª revisión, VERIFICADA CON VISIÓN):** la foto
> `WhatsApp Image 2026-09-09 at 20.18.25.jpeg` muestra la etiqueta original del
> **termostato Eberle Type 17225 7007** (Made in W. Germany):
> `AC 240V — 6 (3,5) A` / `AC 24V — 1 (1) A` / `II 4K/h`.
> Los 6(3,5) A son el rating del contacto bimetal ORIGINAL, no una medición de
> carga. La foto `...20.18.24.jpeg` muestra el cableado real: **solo están
> conectados los terminales 1, 3, 4, 5 y 7** = N 240V, L1 (HOT), COMPRESSOR,
> FAN y SWITCH OUTPUT. Los terminales COOLING y HEATING del Eberle están sin
> usar. **Con 3 SSR es suficiente** (compresor, ventilador, switch output),
> mapeados a los 3 canales actuales del firmware (frío/calor/ventilador).
> **Decidido: se mantiene el límite de software de 1 cambio / 300 s** (12/h,
> 300× por debajo del límite mecánico original de 4.000 ciclos/h).
> Recomendación de compra SSR-25DA + disipador: se mantiene (margen gratis
> para el pico de arranque del compresor; ver §1.3).

### Por qué NO sirven los de 8-16 A "justos"

Un motor monofásico (compresor/ventilador de AC) tiene corriente de arranque de
**6–8× la nominal** durante 0,1–0,5 s. Con 6 A nominales inductivos el pico real
puede llegar a **36–48 A**. Un SSR de 10 A muere en el primer arranque; uno de
16 A sufre. Regla del oficio para SSR con carga de motor: **dimensionar a 3–4×
la corriente nominal** y montar disipador.

### Recomendación: Fotek SSR-25DA (o clón equivalentes serie SSR-xxDA) ×3

| Parámetro | Valor |
|---|---|
| Entrada | 3–32 VDC (LED interno, ~10 mA trigger) ✓ compatible con driver NPN a 3.3 V |
| Salida | 24–380 VAC |
| Corriente nominal | 25 A (con disipador) |
| Conmutación | **Zero-cross** (menos EMI, menos estrés del triac) |
| Surge | ~100 A / ciclo — cubre el arranque del motor con margen |
| Montaje | Tornillo M3/PCB PTH, estándar |
| Precio orientativo | 2,5–5 €/ud (verificar al pedir) |

Con 6 A nominales el margen es 4× — correcto para carga inductiva. Los 3,5 A
resistivos van sobradísimos.

### ⚠️ Disipador OBLIGATORIO

Caída típica del triac ≈ 1,4 V → a 6 A disipa **~8,4 W por SSR**. Sin disipador
el SSR se va a protección térmica (120 °C) o se destruye. Pedir:

- 3× disipador TO-220/SSR de ~1–2 °C/W (los específicos para SSR-25DA, ~1–3 €)
- 3× pasta térmica + tornillería M3
- Los SSR van atornillados a los disipadores FUERA de la zona lógica, con airflow

Alternativa si el ventilador va solo a ~1 A: SSR-10DA solo para ese canal, pero
unificar en 25DA es más simple y más barato en conjunto.

### 1.3 Efecto de que la carga real sea menor

Si la carga real resulta ser ~2–3 A (típico en ventiladores y resistencias de
calefacción pequeñas de split):

- **SSR-25DA sigue siendo la compra correcta**: a 25 DA la diferencia de precio
  con 10DA/16DA es de céntimos/euros, y el pico de arranque del motor (aunque
  la nominal sea baja) sigue siendo 6–8× — el margen gratis no se desperdicia.
- **El disipador puede ser más pequeño**: a 2–3 A la disipación cae a ~3–4 W;
  un disipador de 3–5 °C/W va sobrado. Se puede incluso ahorrar montando los
  3 SSR sobre un único disipador común de ~10 W si el layout lo permite.
- **No bajar de SSR-10DA** aunque la nominal sea 2 A: el pico inductivo manda.
- La creepage AC de 6 mm y el fusible de 5 A del diseño NO cambian: van
  dimensionados por tensión y protección, no por la corriente de carga.

Regla práctica: **comprar el 25DA igualmente** y dimensionar solo el disipador
hacia abajo si la medición con pinza confirma <3 A. Medir de todos modos al
montar: es el dato que cierra el diseño.

### Verificar al recibir (pending P7)

Con 3.3 V GPIO → NPN → LED del SSR: la serie Fotek dispara con ~7.5–10 mA.
El diseño actual (1k base, BC547) entrega ~10 mA al LED. **Margen justo pero
funciona.** Si al montar el SSR real no dispara firme, bajar la R de base de
1k → 470 Ω (sube corriente de base y de LED a ~15 mA, dentro de todo).

---

## 2. Dónde comprar cada pieza

PCBWay ensambla SMD y THT, pero **los módulos (NodeMCU, OLED, RTC, DHT22, SSR)
NO se los pide a PCBWay ensamblar** — son componentes de gran tamaño que se
unen a mano o con su servicio "customer-supplied parts". La división práctica:

### A. PCBWay (pedido principal)

| Ctd | Item | Nota |
|---|---|---|
| 1–5 | PCB 2 capas, 1.6 mm, HASL, ~5×7 cm | El producto real del pedido |
| — | Opcional: ensamblaje SMD de las pasivas | Si se rediseña en KiCad con pasivas SMD 0805 |

### B. LCSC / AliExpress / tienda local (pasivas y semiconductores — baratas y en stock)

| Ctd | Componente | MPN orientativo | Nota |
|---|---|---|---|
| 3 | SSR 25A zero-cross | Fotek SSR-25DA | Ver §1. Si no Fotek, cualquier "SSR 25DA" con entrada 3-32VDC |
| 3 | Disipador SSR ~1–2 °C/W | — | Con pasta térmica |
| 3 | NPN TO-92 | BC547B / 2N2222A | LCSC: BC547B ~0.03 € |
| 3 | R 1 kΩ ¼ W (o 0805) | — | Base |
| 3 | R 10 kΩ ¼ W (o 0805) | — | Pull-down base |
| 2 | R 4.7 kΩ (o 0805) | — | Pull-ups I2C |
| 9 | Cerámico 100 nF 50 V (0805/5 mm) | — | 5 desacoplo + 4 entradas SSR/DHT |
| 1 | Electrolítico 100 µF / 16 V | — | Bulk 3V3 |
| 1 | Portafusibles chasis 250 V + fusible 5 A lento | — | Línea L |
| 1 | MOV 14D471K | — | L-N |

### C. Módulos (AliExpress/local — NO los vende PCBWay como partes de ensamblaje)

| Ctd | Módulo | Nota |
|---|---|---|
| 1 | ESP8266 NodeMCU LoLin v3 | O ESP-12F suelto en revisión futura |
| 2 | OLED SSD1306 128×64 I2C | Cambiar la parte grove_oled_128x96 del .fzz |
| 1 | **DS3231** + CR1220 (NO DS1307) | pending #2 |
| 1 | DHT22 (AM2302) | |
| 2 | Botones + 1 interruptor SPST | El interruptor debe cerrar a GND (pending #14) |
| 1 | Potenciómetro 100K (3362U o perilla) | |
| 4–5 | Bornas de tornillo (AC entrada + 3 salidas SSR) | Paso 5.0/5.08 mm, rated 250V 10A+ |

### D. Mecánica

- Caja con ventana para las 2 OLED (ABS ~120×80×40 mm) o printed
- Pasacables prensaestopas M16 para la entrada AC
- Esquineros/standoffs para la PCB

---

## 3. Cómo se hace el pedido en PCBWay

### 3.1 Archivos que piden (PCB sola)

1. **Gerber RS-274X** (capas: cobre top/bottom, silk, mask, edge cuts) + **drill Excellon**
2. Opcional para ensamblaje: **BOM** (CSV/XLSX) + **CPL/centroid** (X, Y, rotación, side)

### 3.2 Configuración del pedido PCB

- Layers: 2 · Thickness: 1.6 mm · Copper: 1 oz (2 oz si se quisieran trazas AC finas, no necesario)
- Surface finish: HASL (barato) — ENIG no aporta aquí
- Solder mask: el color que quieras; silk blanco
- Quantity: 5 (margen para errores de primer intento; el precio típico es ~5–15 € + envío)
- En "Special requirements" NO poner nada raro; la creepage de 6 mm la pones tú en el layout

### 3.3 ¿Asamblea (PCBA) o PCB sola?

**Recomendado: PCB sola + soldadura manual.** Motivos:
- El 80% de las piezas son módulos y THT de gran tamaño (SSR, bornas, disipadores)
  que PCBWay no puede colocar en máquina
- El ensamblaje SMD mínimo de PCBWay (~15–20 €/tablero + setup) no compensa por
  soldar 12 pasivas y 3 transistores a mano
- Zona AC: quieres soldar tú y revisar tú, no un tercero

Si aun así quieres PCBA de las pasivas: subir BOM CSV + CPL, marcar las pasivas
como "assembly", los módulos como "do not populate" (DNP).

### 3.4 Envío a España

PCBWay envía a España; elegir envío económico (4–8 días, ~5–10 €). Los SSR
disipadores y módulos comprarlos en AliExpress/local para no triplicar portes.

---

## 4. Software

### 4.1 Fritzing (para terminar el .fzz actual) — YA DISPONIBLE en tu Debian

Hay paquete en los repos: `fritzing 1.0.1-1+b6`. Instalar:

```bash
sudo apt install fritzing
fritzing /home/ignacia/thermostat/sketch_pcb.fzz
```

Qué hacer dentro (termina los pendientes §2 del checklist):
1. Cambiar la parte RTC: quitar DS1307 → Parts → buscar "DS3231" (si no está en
   tu librería, descargar módulo DS3231 de fritzinghub/parting-tool y cargarlo
   con Parts → Import)
2. Cambiar OLED `grove_oled_128x96` por SSD1306 128×64
3. Añadir bornas AC, fusible y MOV (buscar "screw terminal", "fuse holder", "MOV"
   en la librería core)
4. Ordenar posiciones visuales de NPN/R/C nuevas (drag)
5. Exportar a PCB: menú **File → Export → Advanced → PCB** → formato **Gerber RS-274X**
   (marca todas las capas + drill Excellon)

⚠️ Limitación honesta: Fritzing 1.x exporta Gerbers funcionales pero **básicos**
(sin control de impedancia, DRC pobre, y a veces errores de capas en diseños con
muchas partes). Para una placa de 2 capas con separaciones AC simples es
suficiente, pero **revisar el Gerber exportado en gerbv o PCBWay viewer antes de pagar**.

### 4.2 KiCad (la vía "profesional", 100% compatible con PCBWay)

```bash
sudo apt install kicad
```

- Formato nativo de la industria; PCBWay tiene plugin oficial **pcbway-kicad** y
  plantilla de pedido directo desde KiCad (File → Fabrication Outputs → Gerbers)
- BOM y CPL (pick&place) se exportan nativamente: `File → Fabrication Outputs →
  Placement Files (.pos)` y BOM con el plugin `kicad-bom` o CSV manual
- **No importa .fzz directamente.** La migración es redibujar (la netlist ya la
  tienes verificada: 19 nets, son ~30 componentes — 1–2 h en KiCad)
- Ventaja real: DRC con reglas de separación AC/DC configurables (Design Rules →
  clearance 6 mm en net class "AC"), que Fritzing NO tiene

### 4.3 Recomendación

- **Si quieres acabar rápido esta semana:** Fritzing (apt), terminar el .fzz,
  exportar Gerber, revisar en https://gerber-viewer.pcbway.com o gerbv, pedir.
- **Si quieres margen de seguridad en la zona AC y una segunda revisión limpia:**
  redibujar en KiCad con net class AC de 6 mm de clearance. Es la vía que
  recomiendo para 220 V, pero no bloqueante.

Complementos útiles:
```bash
sudo apt install gerbv      # visor de Gerbers para verificar antes de pedir
```

---

## 5. Orden de trabajo sugerido

1. [ ] `sudo apt install fritzing gerbv` (5 min)
2. [ ] En Fritzing: DS3231 + OLED 128×64 + bornas/fusible/MOV + ordenar (1–2 h)
3. [ ] Exportar Gerber + drill → abrir en gerbv → verificar capas y creepage
4. [ ] Subir a PCBWay, pedir 5× PCB 2 capas 1.6 mm HASL (PCB sola, sin ensamblaje)
5. [ ] Paralelo: comprar pasivas (LCSC/local) + 3× SSR-25DA + disipadores + módulos
6. [ ] Mientras llega: clamp `/temp` en el .ino + `Secrets.h` (pending #5/#10)
7. [ ] Montaje según checklist.md §5 (primer arranque SIN carga AC)

## 6. Riesgos / verificaciones del pedido

- **Fotek falsificados**: la serie SSR-xxDA está plagada de clones. Los de
  ~2,5 € suelen ser clones OK para esta aplicación, pero si el pico de arranque
  da problemas, comprar marca genuina (Fotek/Chint) o subir a 40DA.
- **Zero-cross vs random**: confirmar que el SSR comprado es zero-cross (los "DA"
  lo son). Con carga resistiva pura da igual; con motor, zero-cross alarga la vida.
- **Medir el arranque real** con pinza amperimétrica en cuanto esté montado: si
  el pico supera ~80 A (poco probable con 6 A nominales), reconsiderar SSR-40DA.
- Precios de este doc son orientativos (búsqueda web 2026-09-10); verificar en el
  carrito de PCBWay/LCSC al pedir.
