# Rev C: 84 × 84 mm con conector FPC para la DWIN 4" sin carcasa

Actualizado: 2026-10-21. **No pedir ni pagar todavía**: faltan las comprobaciones
de la última sección. La Rev B (`REV_B.md`) se conserva tal cual como alternativa.

## Qué cambia respecto a la Rev B

| | Rev B | Rev C |
|---|---|---|
| Pantalla | por cable a J2 (4 hilos) | **DMG48480F040_01WTCZ01** (cristal blanco) enchufada a **J6**, conector FPC de 50 pines y 0,5 mm en la cara que mira a la pantalla. **Sin J2** |
| Montaje SMD | cara superior | **todas las SMD en la cara que mira a la pantalla**, junto a J6: soldadura SMD en **una sola cara** (la inferior); las piezas de patillas, en la superior |
| Encendido | interruptor en J4 (D0, R15) | **desde la pantalla** (teclas 0x0020–0x0022) o con `/power?on=…`; se recuerda tras un corte. **Sin J4 ni R15**; D0 queda libre |
| Montaje de la pantalla | — | **girada 180°**: su FPC sale por el borde superior, se dobla por detrás y baja hasta J6; la imagen se gira en el proyecto DGUS |
| Relés | bobinas a y = 43 | **subidos 4,5 mm** (bobinas a y = 38,5) para dejar sitio a J6 |
| 230 V | borna arriba en horizontal | borna **J20 vertical** en la columna derecha (de arriba abajo: COMP, VENT, CALOR, L) y **F2** debajo |
| Funciones de relé | RL1 COMP, RL2 CALOR, RL3 VENT | **RL1 COMP, RL2 VENT, RL3 CALOR**: la calefacción, que es la carga mayor, tiene la pista más corta. Mismos GPIO: el firmware no cambia |
| NodeMCU | doble huella (LoLin o Amica) | **solo Amica** (filas a 22,86 mm, en y = 55,7 y 78,56); zócalos montados por el fabricante |
| Sensor | DHT22 en J3 (D5) | **SHT40 por I²C** en J3 (3V3, GND, SCL, SDA), en el mismo bus que el RTC (J5) |
| Taladros | (4,4) (80,4) (4,46) (80,80) | (4,4) (**80,38**) (4,46) (80,80) |

## Seguridad eléctrica (validada)

`python3 validate_rev_b.py --design build_rev_c_fzz` → 0 fallos.

| Separación mínima | Medida | Regla |
|---|---|---|
| 230 V ↔ SELV, en cualquier combinación de caras | 8,27 mm | ≥ 8,0 mm (aislamiento reforzado) |
| Entre redes de 230 V | 2,54 mm | ≥ 2,4 mm |
| SELV, incluidos los pines de 0,5 mm del FPC | 0,20 mm | ≥ 0,20 mm |
| Cuerpos de las piezas inferiores ↔ soldaduras THT | 0,04 mm | sin solape (con 0,5 mm de margen alrededor de cada pad) |

- Pistas de 230 V de 2,5 mm; la del ventilador, de 2,0 mm, porque pasa a 4,8 mm de los contactos de RL3 (el ventilador consume poco). Con cobre de 2 oz hay más margen.
- **Lámina aislante obligatoria:** el cable de la pantalla se dobla sobre la zona de 230 V de la cara delantera. Entre la PCB y la pantalla va una lámina de policarbonato o poliéster V-0 de ≥ 0,4 mm que cubre toda la zona por encima de la línea discontinua. Hay que cortar a ras (≤ 1,5 mm) las patillas de 230 V de esa cara.

## Conector de la pantalla (J6)

- JUSHUO **AFC07-S50ECA-00** (LCSC C262650): 0,5 mm, 50 pines, contacto superior, cierre deslizante, 2,0 mm de alto. Va en la **cara inferior**, con el resto de las SMD.
- Pines usados (hoja de DWIN): 1–2 = +5 V, 3–5 = GND, 49 = TX2 → 1 kΩ → D3, 50 = RX2 ← 1 kΩ ← D4. El resto queda sin conectar.
- Posición medida en el **modelo 3D oficial de DWIN** (`3D-DMG48480F040_01W.zip`, leído con OpenCASCADE). El FPC mide 52,3 mm desde el borde del LCD, que queda 2,14 mm hacia dentro del cristal, y la cola ocupa de 19,2 a 44,7 mm desde el borde del cristal, igual que en el plano. Doblado detrás de la pantalla, su extremo llega a y ≈ 50,9 mm. J6 lo recoge con unos 2 mm de holgura (pads a y = 49,7).
- Fritzing no exporta la pasta ni la serigrafía de la cara inferior: las genera `package_rev_b.py`. Además comprueba que **los 97 pads SMD** están en el cobre inferior exactamente donde dice el diseño y que no hay ninguno en el superior. Fritzing a veces se cuelga al exportar (fallo 139): basta con repetir.

## El cable doblado de la pantalla (comprobado en la caja v10)

- No toca nada. El punto más bajo, el chip T5L, queda a **0,45 mm** de la lámina aislante; la cola, a **1,8 mm**. Las SMD de la cara delantera quedan fuera de su recorrido.
- La lámina aislante (≥ 0,4 mm, V-0) cubre la zona de 230 V **y todo el recorrido del cable hasta 0,9 mm antes de J6**, incluidas las patillas de las bobinas, que hay que cortar a ≤ 1,5 mm. Así, aunque el cable se apoye, solo toca la lámina.

## Ficheros

| Qué | Dónde |
|---|---|
| Generador / Fritzing | `build_rev_c_fzz.py` → `thermostat_rev_c.fzz` |
| Validación | `validate_rev_b.py --design build_rev_c_fzz` |
| Paquete | `package_rev_b.py --design build_rev_c_fzz` → `pcbway/thermostat_rev_c/` |
| Gerber + taladro (PCBWay y JLCPCB) | `pcbway/thermostat_rev_c/thermostat_rev_c_GERBER.zip` (incluye la pasta inferior) |
| BOM / centroides | `pcbway/thermostat_rev_c/pcbway/`, `.../jlcpcb/`, `BOM_MANUAL_ES.csv` (J6 con capa «Bottom») |
| Esquema y vistas | `pcbway/thermostat_rev_c/ESQUEMA_REV_C.svg/png`, `VERIFICACION_TOP/BOTTOM.png` |
| Firmware | `firmware/thermostat_rev_b/thermostat_rev_b.ino` (común a B y C) |
| Caja v10 | `carcasa/build_carcasa_v10.py` → `render_v10.html`, `esquema_v10.svg` |

## Firmware

Compila (2026-10-21, core ESP8266 3.1.2) en dos variantes:
- **Por defecto, SHT40** (Adafruit SHT4x 1.0.5): I²C en D1/D2, dirección 0x44, alta precisión y sin calentador. Si no responde, lo reintenta y, sin lectura válida durante 1 minuto, apaga todo.
- **`-DUSE_DHT22=1`:** DHT22 en D5, para la Rev B.
- **Encendido por software** (Rev C): teclas DGUS 0x0020 (alternar), 0x0021 (encender) y 0x0022 (apagar), y `/power?on=true|false`. Apagado = todas las salidas fuera y la pantalla solo muestra datos. Con `-DUSE_ONOFF_SWITCH=1` vuelve el interruptor de J4 (Rev B).
- **OTA por WiFi:** en la Rev C el USB de la Amica queda dentro de la caja. La primera carga se hace por USB en el banco y las siguientes con ArduinoOTA (nombre `termostato`, contraseña opcional `OTA_PASSWORD` en `Secrets.h`). Mientras se actualiza, todas las cargas quedan apagadas.

## Caja v10

89,6 × 89,6 × **29,15 mm**: el mismo frente que la v9 y 2 mm más de fondo, para el conector, el FPC doblado y la lámina. Cristal blanco con el marco de la caja en blanco. Cápsula del SHT40 de **20 × 20 × 3 mm** bajo la pared inferior, con paredes de 0,6 mm: el módulo SHT40 debe medir ≤ 18,8 × 18,8 × 1,8 mm, es decir, un módulo mini de unos 10 × 10 mm sin pines soldados. Sin agujero USB. Sin interferencias en el modelo.

## Pendiente antes de pedir

1. Las medidas del FPC salen del modelo 3D de DWIN, así que no hace falta esperar a la pantalla para pedir. Cuando llegue, conviene medir el cable estirado (≈ 52 mm desde el borde del LCD) y confirmar el lado del pin 1 antes de montar.
2. Pedir a PCBWay presupuesto con montaje SMD **solo por la cara inferior** y las piezas de patillas por la superior, y que revisen:
   - la huella del HF115F/005-1ZS3 frente a la hoja de Hongfa (COM, NO, NC);
   - la huella del AFC07 frente a su plano.
3. Elegir el módulo SHT40 (formato mini, ≤ 1,8 mm de grueso) y confirmar que lleva resistencias de pull-up de I²C. El RTC suele llevarlas: con las dos en paralelo no hay problema.
4. Imprimir `pcbway/thermostat_rev_c/PCB_REV_C.svg` a 1:1 y presentar relés, borna, fusible, zócalos y JST.
5. Banco a 5 V: relés, arranque con la pantalla conectada (GPIO0/GPIO2), SHT40, OTA y consumo (< 1,1 A).
6. Lámina aislante cortada a medida. La instalación de 230 V, revisada por un electricista.
