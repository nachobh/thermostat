# Pinout y montaje — placa universal Rev A

Diseño vigente: `thermostat_universal.fzz`, 100 × 100 mm, 2 capas, **sólo SELV**.
La numeración siguiente empieza en **pin 1 = pad cuadrado/marcado** de cada
conector; no deducirla por el sentido del cable visto desde atrás. Comprobar con
multímetro continuidad y polaridad en cada mazo terminado antes de conectar
NodeMCU, módulos o SSR. La vista esquemática automática de Fritzing no es una
guía de montaje legible; esta tabla y el propio netlist son la referencia.

| Ref. | Tipo | Pin 1 | Pin 2 | Pin 3 | Pin 4 | Pin 5 |
|---|---|---|---|---|---|---|
| J1 | JST-XH 3 | 5 V de USB/Vin NodeMCU | 3V3 NodeMCU | GND | | |
| J2 | JST-XH 4 | D6/GPIO12 FAN | D8/GPIO15 HEAT | D7/GPIO13 COMP | D5/GPIO14 DHT | |
| J3 | JST-XH 4 | D1/GPIO5 SCL | D2/GPIO4 SDA | A0 | GND | |
| J4 | JST-XH 4 | D0/GPIO16 | D3/GPIO0 | D4/GPIO2 | GND | |
| J5 | JST-XH 4 | 3V3 | GND | SCL | SDA | |
| J6 | JST-XH 4 | 3V3 | GND | SCL | SDA | |
| J7 | JST-XH 4 | 3V3 | GND | SCL | SDA | |
| J8 | JST-XH 3 | 3V3 | DHT DATA | GND | | |
| J9 | JST-XH 3 | 3V3 | POT WIPER/A0 | GND | | |
| J10 | JST-XH 5 | D0 | D3 | D4 | GND | 3V3 |
| J11 | MKDS 2 | +5V SSR COMP (4) | CTRL− COMP | | | |
| J12 | MKDS 2 | +5V SSR HEAT (1) | CTRL− HEAT | | | |
| J13 | MKDS 2 | +5V SSR FAN (3) | CTRL− FAN | | | |

J5 = OLED 1, J6 = OLED 2, J7 = RTC DS3231. Confirmar que las direcciones de las
dos OLED son distintas: 0x3C y 0x3D. J9 conecta los extremos del potenciómetro
a 3V3/GND y el cursor a A0. **Antes de conectar J9, medir el rango admitido por
el A0 del NodeMCU real**: algunas placas integran divisor a 3,3 V y otras no.
Si A0 sólo admite 1,0 V, añadir divisor externo apropiado en el mazo.

## Mandos y estados seguros

- Interruptor de habilitación: entre **J10 pin 1 D0 y pin 5 3V3**. Cerrado =
  habilitado; abierto/cable desconectado = apagado. R15 tira D0 a GND. **Nunca
  conectar el viejo interruptor entre D0 y GND**: era la lógica incorrecta.
- Pulsador MENU: entre J10 pin 2 D3 y pin 4 GND. Pulsador SELECT: entre J10
  pin 3 D4 y pin 4 GND. R16/R17 tiran ambos pines a 3V3. No mantener pulsados
  durante reset/encendido: GPIO0 y GPIO2 participan en el arranque ESP8266.
- J4 es el mazo hacia el NodeMCU; J10 va a los mandos externos. Ambos comparten
  D0/D3/D4/GND, pero **J4 no aporta 3V3**; ésta llega por J1.

## Driver de cada relé externo (decisión 2026-10-21: relés HF115F, no SSR)

```text
J1 +5 V ── F1 PTC 0,30 A ── J11/12/13 pin 1 ── bobina relé +  ┐ diodo 1N4007/1N4148
GPIO ── 1 kΩ ── base BC547B ── 10 kΩ ── GND                    │ en los terminales de
                       emisor ─────────── GND                  │ la bobina, CÁTODO al
                       colector ── J11/12/13 pin 2 ── bobina − ┘ lado +5 V (pin 1)
```

- Relé: **Hongfa HF115F/005-1ZS3** (o 1ZS3A, contactos AgSnO₂): bobina 5 V, 62 Ω ±10 %
  (≈ 80 mA, 400 mW), cierre 3,5 V máx., apertura 0,5 V mín.; contacto 16 A 250 VAC
  **solo en el contacto NO** (en la versión 1Z), 9 A 250 VAC cos φ 0,4. Usar COM + NO.
  29 × 12,7 × 15,7 mm; aislamiento bobina–contactos 5 kV, distancia de fuga 10 mm.
  Datos de `Descargas/hf115f.pdf` (Hongfa, rev. 1.00, 2011).
- **Diodo obligatorio en cada bobina** (la PCB no lo lleva): sin él, el pico inductivo al
  apagar puede superar los 45 V del BC547B. No hace falta resistencia en serie.
- **Presupuesto de bobinas:** F1 (RXEF030) retiene 0,30 A a 23 °C y menos con calor.
  Dos bobinas a la vez ≈ 160 mA: admisible. **Tres a la vez no.** El firmware impide
  calefacción + compresor simultáneos y apaga todo si hubiese más de 2 bobinas activas.
- **Antiarranque del compresor:** 5 min entre cambios térmicos y desde el arranque
  (`THERMAL_CHANGE_MS` en `thermostat.ino`); el apagado nunca se retrasa.
- BC547B a ≈ 80 mA: dentro de su máximo de 100 mA, sin mucho margen; comprobar
  temperatura y V_CE en banco.
- Los contactos del relé van a una **mini-placa de potencia aparte** (ver
  `carcasa/`), nunca a J11–J13. La PCB no contiene 240 V ni conductores de 240 V.

## Población de Rev A

- Montar R1/R3/R5 = 1 kΩ; R2/R4/R6/R15/R16/R17 = 10 kΩ.
- Montar R10–R14 = puentes 0 Ω; son **obligatorios**, no DNP.
- R7/R8 (I²C) y R9 (DHT) = 4,7 kΩ **DNP inicialmente**; poblar sólo si los
  módulos no traen la resistencia necesaria, tras medir los pull-ups efectivos.
- Montar F1 RXEF030, Q1–Q3 BC547B con orientación C-B-E comprobada en la pieza
  real, C1–C3/C7/C9 = 100 nF, C8 = 100 µF y C10 = 47 µF. Respetar el positivo
  de C8/C10; C8 va a 5 V y C10 a 3V3.
- El cargador USB aislado 5 V/1 A alimenta **al NodeMCU**. J1 pin 1 recibe los
  5 V de USB/Vin y J1 pin 2 recibe la salida regulada 3V3 de esa placa. No
  inyectar 5 V al pin 3V3. **Medir en el NodeMCU concreto** que Vin entrega 5 V
  cuando se alimenta por USB; las variantes de placa no son idénticas.

## Verificaciones antes de energizar

1. Presentar J1–J10, J11–J13, Q1–Q3, F1 y pasivas sobre impresión 1:1; medir
   paso, ancho, taladros y espacio para carcasa y cables.
2. Medir continuidad de cada pin de la tabla, ausencia de cortocircuito entre
   5 V/3V3/GND y entre salidas SSR; verificar los puentes 0 Ω.
3. Alimentar sólo con 5 V y sin SSR: confirmar 3V3, D0 LOW con interruptor
   abierto, D3/D4 HIGH sin pulsar y D8/GPIO15 LOW durante arranque.
4. Simular las tres entradas SSR con cargas de prueba a 5 V y verificar los
   estados de apagado, encendido y fallo. Sólo después conectar SSR externos.

Referencias de huellas: [JST XH](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf),
[Phoenix Contact 1715721](https://www.phoenixcontact.com/en-sg/products/printed-circuit-board-terminal-mkds-15-2-508-1715721),
[Littelfuse RXEF030](https://www.littelfuse.com/assetdocs/littelfuse_ptc_radial_leaded_rxef_datasheet?assetguid=e9a7b6b3-79ce-478c-a39a-0a70ee48ccec).
