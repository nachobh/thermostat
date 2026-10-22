# Checklist de fabricación

Actualizado: 2026-10-01. Para pedir la PCB desnuda bloquean las comprobaciones
físicas de huellas/fijación de las secciones 1–2, la revisión independiente de
la sección 5 y la aceptación del visor/DFM de PCBWay. Las pruebas de firmware,
banco y potencia de las secciones 3–4 bloquean la instalación, no la fabricación.

## 1. Esquema y piezas físicas

- [x] Borne Eberle 1 = calefacción, 3 = ventilador, 4 = compresor.
- [x] Borne 5 = L, 7 = N 240 V; 0/2/6 sin conexión en las fotos.
- [x] PCB sólo SELV; tres SSR y toda la red externos.
- [x] Tres drivers: `GPIO→1k→B`, `10k B→GND`, `E→GND`, `C→CTRL-`, `+5V→SSR+`.
- [x] D8/GPIO15 dispone de pull-down físico y latch LOW antes de OUTPUT.
- [x] NodeMCU externo por mazo; no tiene huella en el PCB.
- [ ] Presentar un BC547B real y confirmar C-B-E.
- [x] Módulos externos conectados por JST-XH, sin huellas de OLED/RTC.
- [ ] Confirmar que un OLED se puede configurar a 0x3D y el otro a 0x3C.
- [ ] Medir pull-ups I2C de los módulos; dejar las 4,7 kΩ de placa DNP si ya
      existen suficientes en paralelo.
- [ ] Presentar físicamente JST-XH 3/4/5, MKDS, PTC y pasivas sobre impresión
      1:1; los sensores y mandos son externos.
- [ ] Verificar rango A0 del NodeMCU real; añadir divisor en mazo si precisa.
- [ ] Verificar cableado del interruptor D0–3V3 (cerrado = ON) y pulsadores
      D3/D4–GND; no mantener pulsados durante el arranque.

## 2. PCB y Gerbers

- [x] Una sola placa de 100 × 100 mm.
- [x] Cobre antiguo no verificado eliminado.
- [x] Huellas dentro del borde; NodeMCU/antena fuera de la PCB.
- [x] Serigrafía de bornas `+/-` y referencias J11 COMP4, J12 HEAT1, J13 FAN3;
      tabla de pines completa en `PINOUT_Y_MONTAJE.md`.
- [x] 25 redes SELV ruteadas; validador geométrico: 0 infracciones ≥0,20 mm.
- [x] Gerber/Excellon exportados y abiertos en `gerbv`.
- [x] Cuatro taladros NPTH Ø3,0 mm a 5 mm de cada borde; centros 90 × 90 mm,
      zona de radio 3,5 mm sin componentes ni cobre.
- [ ] Imprimir PCB 1:1 y presentar todas las piezas físicas.
- [ ] Confirmar caja, altura de bornas, salida de mazos y tornillería real; un
      agujero nominal de 3,0 mm puede quedar justo para un tornillo M3.
- [x] Gerbers sólo conectan señales SELV; no existe pad/bornal de red.

## 3. Firmware y banco SELV

- [x] Nombres de pines coherentes con las salidas reales.
- [x] WiFi y RTC tienen fallback; el servidor continúa atendiendo.
- [x] DHT usa media válida de 60 s, descarta ±2 °C y falla apagando.
- [x] `/temp` valida 15–30 °C y no es sobrescrito hasta mover el mando.
- [x] `/hot`/`/heating`, `/cold`/`/compressor` y `/fan` conservados.
- [x] Activaciones remotas requieren `confirm=true`.
- [x] Los apagados de calefacción/compresor no esperan el temporizador de
      rearranque; una activación web sin muestra DHT reciente se rechaza.
- [x] Credenciales retiradas a `Secrets.h` local.
- [x] D0 tiene pull-down físico y `INPUT_PULLDOWN_16`; desconexión = OFF.
- [x] D3/D4 tienen pull-ups físicos de 10 kΩ y `INPUT_PULLUP`.
- [x] Compila con Arduino CLI 1.5.1, core ESP8266 3.1.2, DHT 1.4.7,
      RTClib 2.1.4 y U8g2 2.36.19 para `nodemcuv2`, sin credenciales WiFi.
- [ ] Flashear y probar reset/boot con los tres drivers conectados.
- [ ] Medir GPIO15 LOW durante arranque.
- [ ] Probar fallos de DHT, RTC y WiFi y el interruptor físico OFF.
- [ ] Probar anti-ciclo, exclusión calor/compresor y ventilación obligatoria.

## 4. Potencia externa

- [ ] Medir corriente de marcha y pico de arranque de 1, 3 y 4.
- [ ] Verificar cada SSR-40DA barato individualmente antes de instalarlo.
- [ ] Dimensionar disipadores con la medida real; ensayo de una hora a carga.
- [ ] Seleccionar protección de L según conductor, carga, pico y protección
      aguas arriba; registrar valor, curva y poder de corte.
- [ ] Instalar TMOV 275 VAC después de la protección, con conexión L-N corta.
- [ ] Cubrir bornes, fijar cables y mantener barrera/8 mm frente a SELV.
- [ ] Decidir si hace falta seccionador/contactor ante fallo del SSR en corto.

## 5. Pedido: elegir opción A o B

**Decidido 2026-10-19: opción B (PCBWay turn-key THT, suministra y monta todo lo posible).**

- [ ] Segunda revisión **por otra persona** de esquema, PCB y Gerbers; la
      revisión documental automatizada está en `VERIFICACION_HUELLAS.md`.
- [ ] Subir el ZIP al visor/DFM de PCBWay y comprobar que acepta sus ocho capas,
      100 × 100 mm y taladros; no pagar si muestra discrepancias.
- [ ] Opción A: PCB desnuda, 2 capas, 1,6 mm, 1 oz, HASL; revisar la BOM manual
      y presentar los componentes propios sobre la plantilla 1:1.
- [ ] Opción B: mismos Gerbers, montaje THT turn-key de 38 referencias según
      `BOM_PCBWAY_TURNKEY.csv`; R7–R9 DNP. Confirmar oferta, disponibilidad,
      polaridades, huellas y cualquier sustitución propuesta por PCBWay.
- [x] El XY bruto de Fritzing no se envía: F1 aparece erróneamente como SMT;
      `COLOCACION_THT_REFERENCIA.csv` es la tabla corregida y orientativa.
- [ ] No generar una imagen/carga AC como parte de una prueba automática.

## Relés HF115F (añadido 2026-10-21)

- [x] Hoja de Hongfa revisada (`Descargas/hf115f.pdf`): 29 × 12,7 × 15,7 mm, bobina 5 V 62 Ω, 16 A 250 VAC solo contacto NO (1Z).
- [ ] Confirmar que el anuncio de AliExpress es exactamente HF115F/005-1ZS3 (o 1ZS3A), 5 V, paso 5 mm, 16 A; mejor distribuidor con trazabilidad (p. ej. LCSC C9225).
- [ ] Soldar diodo 1N4007/1N4148 en cada bobina (cátodo a +5 V) antes de conectar a J11–J13.
- [ ] Medir corriente de bobina real (≈ 80 mA) y V_CE del BC547B en banco; comprobar temperatura de F1.
- [ ] Firmware: prueba en banco del límite de 2 bobinas y del antiarranque de 5 min (no compilado en este equipo: falta arduino-cli/core ESP8266).
- [ ] Diseñar la mini-placa de potencia (100 × 28 mm, ≥ 8 mm de la zona SELV) y medir huella real del relé: 5 mm, 16 A, cuadrícula 2,52 mm, taladros Ø1,3 (hoja p. 4).
- [ ] Contrastar corriente real de compresor, ventilador y calefactor con la placa de características.

## Pantalla grande (v5, añadido 2026-10-21)

- [ ] Confirmar modelo DWIN DMG48480 (táctil capacitivo `…_03WTC` o sin táctil), plano mecánico, niveles UART y consumo; ver `carcasa/PANTALLA_V5.md`.
- [ ] Reescribir `thermostat.ino` para UART/DWIN (D3 RX, D4 TX) en lugar de U8g2/OLED y pulsadores; diseñar la interfaz con DGUS Tool.
- [ ] Comprobar arranque con la pantalla conectada a GPIO0/GPIO2.
- [ ] Imprimir `stl_v5/` solo tras medir la pantalla real.

## v6: solo pantalla 7" sin potenciómetro (añadido 2026-10-21)

- [ ] Confirmar variante UART del DWIN 7" (04WTC), su plano mecánico y consumo; prever cargador 5 V ≥ 2 A y bornero común de 5 V (`carcasa/PANTALLA_V6.md`).
- [ ] Compilar con `-DUSE_POT=0` y comprobar en banco que A0 flotante no mueve la consigna.
- [ ] Imprimir `stl_v6/` solo tras medir la pantalla real.

## v7: DWIN 5,7" 4:3 sin potenciómetro (añadido 2026-10-21)

- [ ] Elegir variante DWIN 5,7" con UART TTL 3,3 V y táctil capacitivo; descartar RS232 de ± 12 V sin convertidor (`carcasa/PANTALLA_V7.md`).
- [ ] Conseguir plano mecánico (grosor 17,1–18,9 mm, orificios, área activa) y consumo; cargador ≥ 2 A.
- [ ] Imprimir `stl_v7/` solo tras medir la pantalla real.

## v8: sin tapa frontal, pantalla pegada sobre las paredes (añadido 2026-10-21)

- [ ] Elegir entre v8 (144,8 × 110,2 × 68,9 enrasada) y v7 sin tapa (161 × 122 × 47,3): ver `carcasa/PANTALLA_V8.md`.
- [ ] Probar el pegado (cinta de espuma acrílica ≥ 1 mm) con una pantalla/maqueta antes de montar la real; definir salida del mazo de la pantalla con el plano de DWIN.
- [ ] Imprimir `stl_v8/` solo tras medir la pantalla real.

## Rev B 84 × 84 con relés en placa + DWIN 4" + caja v9 (añadido 2026-10-21)

- [ ] Pedir a PCBWay que deje en espera (pedido Rev A) (Rev A); no pagar JLCPCB.
- [ ] Confirmar DWIN 4" 480 × 480 sin carcasa con UART TTL 3,3 V (DMG48480F040_01WTC o equivalente): plano, conector, consumo y RTC.
- [ ] Medir la NodeMCU real y decidir las filas de los zócalos (exteriores LoLin v3 / interiores Amica).
- [ ] Imprimir `pcbway/thermostat_rev_b/PCB_REV_B.svg` a 1:1 y presentar relés, borna J20, fusible F2, JST y zócalos.
- [ ] Comprobar con el polímetro el pinout de un HF115F (COM central, NC junto a la bobina).
- [ ] Revisar Gerber y CPL en el visor del fabricante (D1–D3 a 180°).
- [ ] Hacer el proyecto DGUS según `firmware/thermostat_rev_b/DWIN_DGUS_REV_B.md`; flashear y probar en banco a 5 V.
- [ ] Imprimir la caja v9 en material V-0 solo tras medir pantalla y NodeMCU; tornillos de nailon.

## Rev C: conector FPC para la DWIN F040, Amica, SHT40 y caja v10 (añadido 2026-10-21)

- [ ] Al recibir la DWIN: comprobar el FPC (≈ 52 mm desde el borde del LCD, según el modelo 3D de DWIN) y el lado del pin 1 antes de montar (`REV_C.md`).
- [ ] Cargar el proyecto DGUS con el HDL662S (rotación de 180°) antes de montar la pantalla.
- [ ] Elegir un módulo SHT40 mini (≤ 1,8 mm de grueso) para la cápsula de 20 × 20 × 3 mm.
- [ ] Pedir presupuesto a PCBWay con montaje por las dos caras y revisión de las huellas del HF115F y del AFC07 (texto en `pcbway/thermostat_rev_c/LEEME_PEDIDO.md`).
- [ ] Comprar o cortar una lámina aislante V-0 de ≥ 0,4 mm para la zona de 230 V entre la PCB y la pantalla.
- [ ] Primera carga del firmware por USB en el banco; las siguientes, por OTA.
- [ ] Rev C sin J2/J4: hacer en DGUS las teclas de encendido (0x0020–0x0022); comprobar que el estado se recuerda tras quitar la alimentación.
