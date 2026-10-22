# Rev B: placa de 84 × 84 mm con relés, para DWIN 4" 480 × 480

> Hay una Rev C (`REV_C.md`) con conector FPC para la DWIN F040, NodeMCU Amica y SHT40: es la candidata. La Rev B queda como alternativa (pantalla por cable a J2, DHT22).

Actualizado: 2026-10-21. **No pedir ni pagar todavía**: faltan las comprobaciones
de la última sección. La Rev A (100 × 100, solo SELV) queda congelada como
referencia; el pedido PCBWay (pedido Rev A) debe quedar en espera.

## Qué cambia respecto a la Rev A

| | Rev A | Rev B |
|---|---|---|
| Tamaño | 100 × 100 mm | **84 × 84 mm** (= DWIN 4" sin carcasa, DMG48480F040_01WTC) |
| Relés | externos (mini-placa aparte) | **3 × HF115F/005-1ZS3 en la placa** |
| 230 V | ninguno en la PCB | banda superior: borne J20 (L, COMP, CALOR, VENT), fusible F2 T6,3 A |
| NodeMCU | externo por JST | **sobre zócalos** (doble huella: filas a 1,1" LoLin v3 y a 0,9" Amica) |
| Interfaz | 2 OLED + potenciómetro + pulsadores | **pantalla DWIN táctil por UART** (J2) |
| Pasivos / transistores | THT (BC547B) | **SMD** (BC817-40, 1N4148W, 0805) |
| 5 V | cargador externo | cargador externo aislado ≥ 2 A por J1 + PTC F1 1,1 A |

## Seguridad eléctrica (validada con `validate_rev_b.py`)

- Todo el cobre de 230 V está por encima de la línea discontinua de la serigrafía.
  Distancia mínima medida 230 V ↔ SELV: **11,2 mm** (regla: ≥ 8 mm, aislamiento reforzado),
  en cualquier combinación de caras.
- Entre redes de 230 V: ≥ 2,54 mm (regla ≥ 2,4 mm). Pistas de 230 V de 2,5 mm de ancho.
- El aislamiento bobina–contacto lo da el propio relé (5 kV, 10 mm de fuga según la hoja de Hongfa).
- Taladros de montaje sin metalizar Ø3,2 mm con **tornillos de nailon**; los dos superiores
  están en la zona de 230 V (cobre de 230 V a ≥ 4 mm).
- La caja debe ser de material V-0 (no PLA), con tabique entre la zona de 230 V y la SELV
  y entradas de cable separadas (caja v9).
- El fusible F2 protege las pistas; el circuito sigue necesitando su magnetotérmico.

## Conectores

| Ref | Pines (1 → n) | Notas |
|---|---|---|
| J20 | L · COMP · CALOR · VENT | 230 V. COMP = borne 4 del Eberle, CALOR = 1, VENT = 3. Sin neutro |
| J1 | +5V · GND | cargador USB aislado 5 V ≥ 2 A |
| J2 | +5V · GND · TX · RX | DWIN: TX pantalla → 1 kΩ → D3/GPIO0; RX pantalla ← 1 kΩ ← D4/GPIO2. **Solo UART TTL 3,3 V** |
| J5 | 3V3 · GND · SCL · SDA | RTC DS3231 (opcional) |
| J3 | 3V3 · DATA · GND | DHT22 (pull-up R9 10 kΩ ya en placa) |
| J4 | D0 · 3V3 | interruptor ON/OFF (R15 a GND: cable suelto = OFF) |

Relés: RL1 = compresor (D7), RL2 = calefacción (D8), RL3 = ventilador (D6).
Contactos: columna central **COM**, la más próxima a la bobina **NC** (sin usar) y la
del extremo **NO**. Comprobar con el polímetro (COM–NC cerrado en reposo) antes de soldar.

## Ficheros

| Qué | Dónde |
|---|---|
| Generador / proyecto Fritzing | `build_rev_b_fzz.py` → `thermostat_rev_b.fzz` (PCB + esquema con etiquetas de red) |
| Validación geométrica | `validate_rev_b.py` (0 fallos) |
| Exportación y paquetes | `package_rev_b.py` → `pcbway/thermostat_rev_b/` |
| Gerber + taladro (PCBWay y JLCPCB) | `pcbway/thermostat_rev_b/thermostat_rev_b_GERBER.zip` |
| PCBWay | `pcbway/thermostat_rev_b/pcbway/BOM_PCBWAY.csv`, `CENTROID_PCBWAY.csv` |
| JLCPCB | `pcbway/thermostat_rev_b/jlcpcb/BOM_JLCPCB.csv`, `CPL_JLCPCB.csv` |
| BOM en castellano | `pcbway/thermostat_rev_b/BOM_MANUAL_ES.csv` |
| Esquema | `pcbway/thermostat_rev_b/ESQUEMA_REV_B.svg` / `.png` |
| Vistas de los Gerber | `pcbway/thermostat_rev_b/VERIFICACION_TOP.png`, `VERIFICACION_BOTTOM.png` |
| Firmware | `firmware/thermostat_rev_b/thermostat_rev_b.ino` + `DWIN_DGUS_REV_B.md` |
| Caja v9 | `carcasa/build_carcasa_v9.py` → `carcasa/render_v9.html`, `esquema_v9.svg` |

Regenerar todo: `python3 build_rev_b_fzz.py && python3 validate_rev_b.py && python3 package_rev_b.py`,
y después `python3 carcasa/build_carcasa_v9.py` (usa la vista de los Gerber como textura).

## Firmware

`firmware/thermostat_rev_b/thermostat_rev_b.ino` compila (2026-10-21) para
`esp8266:esp8266:nodemcuv2` con el core 3.1.2, DHT sensor library 1.4.7 y RTClib 2.1.4
(`arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 firmware/thermostat_rev_b`).
No se ha flasheado ni probado con hardware.

- Misma lógica de control que la Rev A: histéresis 0,5 °C, antiarranque de 5 min,
  calor y frío nunca a la vez, ventilador obligatorio con carga térmica, todo OFF si
  el sensor no da lectura válida en 1 min o si J4 está en OFF.
- Sin potenciómetro: la consigna se cambia desde la pantalla (± 0,5 °C) o con
  `/temp?temp=22.5`, y se guarda en flash 10 s después del último cambio.
- Pantalla: protocolo DGUS (`5A A5 …`, 115 200 baudios por defecto); variables y
  códigos de tecla en `DWIN_DGUS_REV_B.md`. Hay que hacer el proyecto de pantallas con
  DGUS Tool siguiendo ese mapa.
- Se mantienen los endpoints HTTP de la Rev A (`/temp`, `/heating`, `/compressor`, `/fan`, `/auto`).

## Caja v9

89,6 × 89,6 × 27,15 mm, con la pantalla enrasada al frente (marco de 2,8 mm) y una
cápsula ventilada para el DHT22 de 14 mm bajo la pared inferior. Dos piezas: el marco
(paredes, repisa de la pantalla y ranura para su cable) y la tapa trasera (torretas de
16,5 mm, tabique 230 V / SELV y entradas de cable separadas). La PCB lleva los
componentes hacia atrás. Sin interferencias en el modelo.
Medidas de la pantalla, del módulo NodeMCU y del DHT: **supuestas**.

## Pendiente antes de pedir

1. PCBWay: pedir que dejen en espera (pedido Rev A) (Rev A). No pagar JLCPCB.
2. Confirmar la pantalla exacta (DMG48480F040_01WTC o equivalente) con **UART TTL**, su plano
   (posición del área activa, conector y cable), su consumo y si trae RTC propio.
3. Medir la NodeMCU real: LoLin v3 (filas a 27,94 mm, zócalos en las filas exteriores) o Amica
   (22,86 mm, filas interiores). El taladro de montaje inferior izquierdo está en (4, 46) porque
   el módulo LoLin tapa la esquina.
4. Imprimir `PCB_REV_B.svg` a escala 1:1 y presentar encima relés, borna, fusible, JST y zócalos.
5. Revisar los Gerber en el visor de PCBWay o JLC (máscara, serigrafía y taladros) y las
   rotaciones del CPL en la vista previa de montaje de JLC (diodos a 180°).
6. Banco a 5 V: relés sin carga, arranque con la pantalla conectada a GPIO0/GPIO2 y
   consumo total (< 1,1 A para el PTC).
7. Instalación de 230 V: hacerla o revisarla con un electricista.
