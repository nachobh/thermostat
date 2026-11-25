# Contexto para un asistente de IA (léeme primero)

Este fichero resume el estado del proyecto para poder retomar dudas, correos con el fabricante
o siguientes pasos **sin la conversación original**. Actualizado: **2026-11-25**.

## Estado de puesta en marcha (2026-11-25)

- Ignacio ha recibido las **dos PCB Rev C ensambladas**.
- Se identificó por USB un NodeMCU con CP2102 en `/dev/ttyUSB0` y chip
  **ESP8266EX**. Se compiló y cargó por USB, fuera de la PCB, el firmware
  `firmware/thermostat_rev_b/thermostat_rev_b.ino` en configuración Rev C por
  defecto (`esp8266:esp8266:nodemcuv2`). La escritura terminó con
  `Hash of data verified`; el monitor serie a 115200 muestra el firmware
  ejecutándose y avisando de que **falta SHT40**, esperado sin sensor conectado.
- Esta carga no incluye `Secrets.h` ni credenciales Wi-Fi: la operación es local
  y OTA no está disponible hasta configurar Wi-Fi y volver a flashear.
- **Pendiente:** inspeccionar/medir aislamiento de las PCB recibidas, soldar
  zócalos U1, probar una placa sólo a 5 V con el SHT40, y crear/cargar el
  proyecto DGUS para la pantalla. No se ha probado con 230 V.

Repositorio: <https://github.com/nachobh/thermostat> (rama `main`).
Enlaces de ficheros: `https://github.com/nachobh/thermostat/blob/main/<ruta>`.

## Quién y cómo

- Autor: **Ignacio** (España). Escribe en castellano; los correos al fabricante, en inglés y **firmados «Ignacio»**.
  (El ordenador se llama «ignacia», un juego de palabras con «IA»: no es su nombre.)
- **Las compras y los pagos los hace siempre él.** El asistente redacta correos y prepara ficheros, pero no paga nada.
- Prefiere respuestas directas, paso a paso, con tablas cuando ayudan y sin rodeos.

## Qué es

Termostato con ESP8266 que sustituye a un **Eberle 17225 7007** (230 V). Salidas del Eberle:
borne **1 = calefacción**, **3 = ventilador**, **4 = compresor**, **L**. No usa el neutro.

## Revisión vigente: **Rev C** (pedida)

Documento principal: [REV_C.md](https://github.com/nachobh/thermostat/blob/main/REV_C.md).

| | Rev C |
|---|---|
| PCB | 84 × 84 mm, 2 capas, FR-4 1,6 mm, 1 oz |
| Relés | 3 × **Hongfa HF115F/005-1ZS3** (16 A, bobina 5 V): RL1 = compresor (D7), RL2 = ventilador (D6), RL3 = calefacción (D8). Driver BC817-40 + 1N4148W |
| 230 V | Borna **J20** vertical a la derecha (de arriba abajo: COMP(4), VENT(3), CALOR(1), L) y fusible **F2** TR5 T6,3 A |
| SELV | ≥ 8 mm de cualquier cobre de 230 V (validado: mínimo 8,27 mm) |
| MCU | **NodeMCU Amica** (filas a 22,86 mm) sobre zócalos **U1**; los zócalos los suelda Ignacio (2 tiras hembra 1×15) |
| Pantalla | **DWIN DMG48480F040_01WTCZ01** (4", 480×480, cristal blanco, set con adaptador HDL662S), montada **girada 180°**; su FPC de 50 pines se dobla por detrás y entra en **J6** (JUSHUO AFC07-S50ECA-00, contacto superior, **cara inferior**) |
| Sensor | **SHT40** por I²C en **J3** (3V3, GND, SCL, SDA), en cápsula exterior de 20 × 20 × 3 mm |
| Otros | **J1** = 5 V de un cargador externo (≥ 2 A) con PTC F1 1,1 A · **J5** = RTC DS3231 opcional (I²C) |
| Quitados | J2 (UART por cable), J4 (interruptor ON/OFF) y R15: el encendido se hace desde la pantalla |
| Montaje | **Todas las SMD en la cara inferior** (la que mira a la pantalla): soldadura SMD en una sola cara |

Pines de J6 usados (FPC de DWIN): 1–2 = +5 V, 3–5 = GND, 49 = TX2 → 1 kΩ → D3/GPIO0, 50 = RX2 ← 1 kΩ ← D4/GPIO2.

### Pedido (PCBWay)

- **Pagado el 2026-10-23**: 5 PCB + montaje de 2 placas (oferta de montaje de 29 $), con envío **FedEx IP**.
  El número de pedido y la factura están en el correo de Ignacio. Contacto comercial en PCBWay: «Lynne».
- La BOM enviada es **sin U1**: [BOM_PCBWAY_REV_C_SIN_U1.csv](https://github.com/nachobh/thermostat/blob/main/pcbway/thermostat_rev_c/PARA_SUBIR_PCBWAY/BOM_PCBWAY_REV_C_SIN_U1.csv).
  Sustitución aceptada: **C1 → ERA16V220M6X11** (220 µF 16 V, 6,3 × 11 mm).
- Pregunta de ingeniería contestada: el número de pedido puede ir en la **serigrafía de la cara inferior, junto al borde superior**,
  porque ahí no hay cobre en esa cara; solo serigrafía, sin tocar cobre ni máscara.
- Plazo: 16–18 días de fabricación + FedEx. **FedEx cobrará al entregar el IVA del 21 % y una tarifa de aduana**
  (pagar solo desde la web oficial de FedEx o con el número de seguimiento de PCBWay).
- Ficheros que se subieron y guía del formulario: [PARA_SUBIR_PCBWAY/](https://github.com/nachobh/thermostat/tree/main/pcbway/thermostat_rev_c/PARA_SUBIR_PCBWAY)
  ([LEEME.md](https://github.com/nachobh/thermostat/blob/main/pcbway/thermostat_rev_c/PARA_SUBIR_PCBWAY/LEEME.md),
  [MENSAJE_PCBWAY.txt](https://github.com/nachobh/thermostat/blob/main/pcbway/thermostat_rev_c/PARA_SUBIR_PCBWAY/MENSAJE_PCBWAY.txt)).

### Compras de Ignacio (pedidas)

Pantalla DWIN «01WTCZ01 set», tiras hembra 1×15, módulo SHT40 mini (≤ 1,8 mm de grueso), lámina aislante
(policarbonato 0,5 mm, a ser posible V-0), cargador USB 5 V 2 A con CE y, opcionalmente, un DS3231.

## Al recibir las placas: comprobaciones

Lista completa en [LEEME_PEDIDO.md](https://github.com/nachobh/thermostat/blob/main/pcbway/thermostat_rev_c/LEEME_PEDIDO.md) («Al recibir las placas»). Lo esencial:
1. Con el polímetro: **ninguna continuidad** entre COMP/VENT/CALOR/L y cualquier pin SELV (J1, J3, J5, J6, U1).
2. Relé: COM–NC cerrado en reposo y COM–NO cerrado con 5 V en la bobina. Se supuso **COM en la columna central** del HF115F; no se ha verificado con un relé real.
3. FPC de la pantalla: ≈ 52 mm desde el borde del LCD (medido en el modelo 3D de DWIN) y lado del pin 1 según `REV_C.md`.
4. **Cortar a ≤ 1,5 mm** las patillas de la cara de la pantalla y poner la **lámina aislante** sobre la zona de 230 V y el recorrido del FPC antes de montar la pantalla.
5. Soldar los zócalos U1 (con la NodeMCU puesta para alinearlos) y probar solo a 5 V: relés, arranque con la pantalla, SHT40 y consumo (< 1,1 A).
6. La instalación de 230 V, hecha o revisada por un electricista.

## Firmware

[firmware/thermostat_rev_b/thermostat_rev_b.ino](https://github.com/nachobh/thermostat/blob/main/firmware/thermostat_rev_b/thermostat_rev_b.ino) (común a Rev B y C).
Compila con arduino-cli, `esp8266:esp8266:nodemcuv2` (core 3.1.2) y las librerías Adafruit SHT4x 1.0.5, DHT sensor library 1.4.7 y RTClib 2.1.4.
Compilado y flasheado en un NodeMCU real el 2026-11-25; todavía no probado
insertado en la PCB ni con SHT40/pantalla conectados.

- Por defecto: SHT40, encendido y apagado desde la pantalla o con `/power?on=…`, OTA por WiFi («termostato»). Para la Rev B: `-DUSE_DHT22=1 -DUSE_ONOFF_SWITCH=1`.
- Control: histéresis de 0,5 °C, antiarranque del compresor de 5 min, calor y frío nunca a la vez, ventilador obligatorio con carga térmica y todo apagado si no hay lectura válida en 1 min.
- Pantalla (DGUS II, 115 200 baudios): mapa de variables y teclas en [DWIN_DGUS_REV_B.md](https://github.com/nachobh/thermostat/blob/main/firmware/thermostat_rev_b/DWIN_DGUS_REV_B.md).
  **Pendiente:** hacer el proyecto en DGUS Tool, con la rotación de 180° en `T5L_CFG.CFG` (byte 0x05, bits 1–0 = 10), y cargarlo con el HDL662S.
- La primera carga se hace por USB en el banco; después, por OTA. `Secrets.h` (WiFi) **no está en el repositorio**; ver `Secrets.h.example`.

## Caja v10

[carcasa/render_v10.html](https://github.com/nachobh/thermostat/blob/main/carcasa/render_v10.html) (generada por `carcasa/build_carcasa_v10.py`).
89,6 × 89,6 × 29,15 mm, pantalla enrasada, 4,5 mm entre la PCB y la pantalla. El FPC doblado queda a 0,45 mm de la lámina y no toca nada.
Tabique 230 V / SELV en la tapa trasera, cápsula del SHT40 centrada abajo. Material V-0 (no PLA). **Aún no hay STL de la v10**; hay de la v4 a la v8.

## Cómo regenerar la Rev C (si hay que cambiar algo)

```
python3 build_rev_c_fzz.py                              # Fritzing + enrutado (~1 min)
python3 validate_rev_b.py --design build_rev_c_fzz      # reglas 230 V / SELV; debe dar FAILURES: 0
python3 package_rev_b.py --design build_rev_c_fzz       # Gerber (Fritzing headless), BOM, CPL, pasta y serigrafía inferiores
python3 carcasa/build_carcasa_v10.py                    # render de la caja (usa la vista de los Gerber)
```

Trampas conocidas:
- Fritzing (`xvfb-run fritzing -gerber`) a veces falla con el código 139: basta con repetir.
- Fritzing espeja las piezas de la cara inferior: el generador las pre-espeja y `package_rev_b.py` comprueba los 97 pads SMD.
- Fritzing no exporta pasta ni serigrafía de la cara inferior: las genera `package_rev_b.py`.
- Para la oferta de montaje de 29 $ de PCBWay: ≤ 100 soldaduras THT **por pedido** y una sola oferta por pedido del carrito.

## Historia breve (por qué es así)

- **Rev A** (100 × 100, solo SELV, relés externos): cancelada.
- **Rev B** (84 × 84, relés en placa, pantalla por cable): alternativa conservada ([REV_B.md](https://github.com/nachobh/thermostat/blob/main/REV_B.md)).
- **Rev C:** conector FPC para la pantalla F040 blanca. Ese conector obligó a subir los relés y a pasar la borna y el fusible a la columna derecha.
  Todas las SMD van a la cara de la pantalla para no pagar montaje por dos caras.
  Se descartó poner el conector en otro sitio: el FPC solo mide 52 mm, y con un giro de 90° caería sobre los relés o la zona de 230 V.
- El DHT22 se cambió por el SHT40 (I²C) y el sensor va fuera de la caja por el calor interno (≈ 1,5–2,5 W).

## Otros documentos útiles

[checklist.md](https://github.com/nachobh/thermostat/blob/main/checklist.md) ·
[README.md](https://github.com/nachobh/thermostat/blob/main/README.md) ·
[pcbway/thermostat_rev_c/](https://github.com/nachobh/thermostat/tree/main/pcbway/thermostat_rev_c) (Gerber, BOM, CPL, esquema y vistas).
