# Piezas y pedido PCBWay

Actualizado: 2026-10-01. No comprar ni fabricar hasta cerrar las medidas marcadas
en `checklist.md`.

## PCB SELV

| Cantidad | Pieza | Nota |
|---:|---|---|
| 1 | NodeMCU ESP8266 LoLin | medir ancho, longitud, separación y número de pines |
| 3 | BC547B TO-92 | comprobar patillaje C-B-E del lote |
| 3 | 1 kΩ 1/4 W | GPIO a base |
| 3 | 10 kΩ 1/4 W | base a GND |
| 3 | 100 nF | entrada de cada SSR |
| 3 | 4,7 kΩ | R7/R8 I²C y R9 DHT; DNP salvo que falten en módulos |
| 5 | 100 nF | desacoplo de módulos |
| 1 | 100 µF / ≥10 V | C8, bulk de la rama 5 V SSR |
| 1 | 47 µF / ≥10 V | C10, bulk de 3V3 |
| 1 | PTC RXEF030 | F1, 0,30 A hold en rama +5 V de SSR |
| 5 | puente 0 Ω | R10–R14; imprescindibles para continuidad |
| 3 | borna 2 polos, 5,08 mm | salida `+5V/CTRL-` a SSR externo |
| 2 | OLED SSD1306 I2C | conector según módulo real |
| 1 | RTC DS3231 | conector según módulo real |
| 1 | DHT22 | o DHT11 cambiando `DHTTYPE` |
| 1 | potenciómetro B10K o B100K | ambos barren el rango ADC; confirmar huella |
| 2 | pulsador y 1 interruptor | el interruptor cierra D0 a 3V3 (habilita); abierto = OFF |
| 3 | 10 kΩ 1/4 W | R15 pull-down D0; R16/R17 pull-up D3/D4 |
| 3 | JST-XH 3 vías B3B-XH-A | J1/J8/J9, mazos XHP-3 |
| 6 | JST-XH 4 vías B4B-XH-A | J2–J7, mazos XHP-4 |
| 1 | JST-XH 5 vías B5B-XH-A | J10, mazo XHP-5 |

La PCB no incluye fuente de red: se usa cargador USB aislado 5 V/1 A.

Uno de los OLED debe poder configurarse a dirección I2C 0x3D; el otro queda en
0x3C. Medir las resistencias pull-up efectivas de OLED y RTC antes de poblar las
dos resistencias opcionales de la PCB.

> **Actualización 2026-10-21:** los SSR (SSR-40DA y Sharp S202S01, 8 A máx. con disipador
> grande) se sustituyen por **3 relés Hongfa HF115F/005-1ZS3** (16 A NO, bobina 5 V 80 mA)
> con diodo 1N4007/1N4148 en cada bobina. Ver `PINOUT_Y_MONTAJE.md` y `carcasa/`. La
> tabla siguiente queda como histórico.

## Caja de potencia externa

| Cantidad | Pieza | Requisito |
|---:|---|---|
| 3 | SSR-40DA genérico | 3–32 VDC, 24–380 VAC, zero-cross; candidato económico |
| 3 | disipador para SSR | dimensionar con hasta ~9 W por canal a 6 A |
| 3 | pasta/almohadilla térmica y tornillos | seguir montaje del fabricante |
| 1 | protección de sobrecorriente | en L, valor/curva tras medir carga y conductor |
| 1 | TMOV 275 VAC | p. ej. Littelfuse TMOV14RP275E, después del fusible |
| 1 | caja y cubrebornes | no propagadora, con barrera AC/SELV |
| varios | bornas de red, punteras, prensaestopas | tensión/corriente certificadas |
| opcional | seccionador/contactor mecánico | necesario si se quiere corte garantizado ante SSR pegado |

El SSR-40DA barato evita superar aproximadamente 5 € por unidad y es compatible
con el driver de 5 V, pero su “40 A” es una cifra para condiciones ideales y
normalmente resistivas. No sustituye la prueba de pico de motor ni una ficha
técnica trazable.

## Opciones de pedido PCBWay tras verificar las piezas físicas

- **A, montaje manual:** PCB sola, sin ensamblaje; usar
  `BOM_MONTAJE_MANUAL.csv` y soldar los componentes propios.
- **B, suministro y montaje PCBWay:** la **misma PCB y el mismo ZIP Gerber**,
  con montaje THT turn-key según `BOM_PCBWAY_TURNKEY.csv` e
  `INSTRUCCIONES_PCBA_TURNKEY.md`. PCBWay debe confirmar disponibilidad y
  sustituciones antes de pagar. R7–R9 quedan DNP.
- 2 capas, FR-4 1,6 mm, cobre 1 oz, HASL.
- Gerber RS-274X más taladros Excellon.
- Gerbers y taladros ya exportados en `pcbway/thermostat_universal_rev_a/`;
  revisar de nuevo en `gerbv` antes de subir el ZIP de fabricación.
- Imprimir 1:1 y presentar encima JST-XH, bornas, PTC, transistores y pasivas
  reales. NodeMCU/RTC/OLED son **externos**, no se presentan sobre la PCB.
- Confirmar que no existe ninguna pista o pad de 240 V: sólo `+5V/CTRL-`.

PCBWay ofrece montaje THT, por lo que no hace falta un segundo layout SMD para
la opción B. NodeMCU, RTC y OLED siguen siendo externos en ambas opciones;
la contratación de mazos o módulos sería una cotización aparte.
