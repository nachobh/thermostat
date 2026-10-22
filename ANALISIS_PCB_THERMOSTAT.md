# Análisis técnico del termostato ESP8266

Actualizado: 2026-09-24. La secuencia operativa y los cálculos completos están
en `PASOS_HASTA_PEDIDO.md`.

## Decisiones cerradas

- La foto del Eberle se interpreta literalmente: están conectados 1
  (calefacción), 3 (ventilador), 4 (compresor), 5 (L) y 7 (N a 240 V).
- La PCB será sólo SELV. No llevará SSR de potencia, fusible, MOV ni pistas de
  red; esos elementos serán externos y encerrados.
- Tres salidas externas `+5V/CTRL-`, compatibles con SSR DA de entrada 3–32 VDC.
- D7/GPIO13 = compresor, D8/GPIO15 = calefacción, D6/GPIO12 = ventilador.
- Cada salida usa BC547B low-side, R de base 1 kΩ y pull-down 10 kΩ.
- Alimentación mediante el cargador USB aislado de 5 V/1 A previsto.
- Candidato económico: SSR-40DA genérico zero-cross externo. No se congela su
  huella en la PCB; un cambio de SSR no obliga a repetir la placa.

## Riesgos de hardware aún abiertos

1. `thermostat_universal.fzz` sí está ruteado y validado geométricamente;
   `sketch_pcb.fzz` es histórico. Falta imprimir 1:1 y presentar piezas reales.
2. NodeMCU es externo. Comprobar C-B-E del BC547B real y rango A0 del NodeMCU.
3. OLED y RTC DS3231 externos: confirmar mazos JST-XH y direcciones I²C.
4. Falta medir corriente de régimen y pico de arranque de cada salida. El
   `6 (3,5) A` de la etiqueta es la capacidad del contacto Eberle, no una medida
   individual de las cargas.
5. El SSR barato carece de una curva de motor y trazabilidad fiable; debe probarse
   con disipador. Para garantía industrial hay que aumentar presupuesto.
6. La protección de sobrecorriente debe coordinarse con el conductor, la carga y
   el dispositivo aguas arriba. No se debe elegir sólo por la cifra “40 A” del SSR.

## Verificación eléctrica del `.fzz`

La Rev A se genera con `build_universal_fzz.py` y pasa
`validate_universal_pcb.py`: 25 redes, 41 partes, 103 pads, 0 infracciones de
continuidad/separación con mínimo de 0,20 mm. Gerbers y taladros exportados a
`pcbway/thermostat_universal_rev_a/`. El pinout verificable está en
`PINOUT_Y_MONTAJE.md`.

El siguiente bloque se refiere **sólo al archivo histórico**:

`repair_thermostat_fzz.py` valida para los tres canales:

- pin 0 de borna a Vin/+5 V;
- pin 1 de borna a colector;
- emisor a GND;
- base aislada de Vin;
- una sola placa de 120 × 100 mm;
- cero trazas PCB heredadas.

El XML y el ZIP son válidos y Fritzing 1.0.1 puede abrir/exportar las tres vistas.
Fritzing sigue avisando de puntos terminales ausentes en partes antiguas
importadas; por eso las huellas y el ruteo continúan siendo bloqueantes.

## Firmware corregido

- Las salidas se fijan LOW antes de `pinMode(OUTPUT)`; el pull-down físico de D8
  mantiene el modo de arranque correcto del ESP8266.
- WiFi caducado no bloquea: timeout de 15 s, control local y reintentos.
- RTC ausente no bloquea el control; el anti-ciclo usa `millis()`.
- DHT: muestra cada 2 s, media válida de 60 s, rechazo de desviaciones >2 °C y
  apagado si durante un minuto no queda ninguna muestra válida.
- Endpoints antiguos conservados y aliases descriptivos añadidos.
- Activar calefacción/compresor/ventilador exige `confirm=true`.
- Setpoint web validado 15–30 °C y mantenido hasta mover el potenciómetro.
- Credenciales locales en `Secrets.h`, excluido de git.

## Punto de parada

No subir Gerbers a PCBWay hasta completar todos los bloqueantes de
`checklist.md`. Que una herramienta exporte un ZIP Gerber no equivale a un DRC
correcto ni a una huella físicamente válida.
