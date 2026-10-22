# Thermostat

Termostato ESP8266 para sustituir un Eberle 17225 7007. El cableado observado
usa calefacción (borne 1), ventilador (3), compresor (4), L (5) y N 240 V (7).

**Rev C (2026-10-21, en revisión, la candidata):** como la Rev B, pero con conector FPC
para la DWIN 4" sin carcasa (cristal blanco), NodeMCU Amica, sensor SHT40 por I²C y caja v10.
Ver [REV_C.md](REV_C.md).

**Rev B (2026-10-21, alternativa):** placa de 84 × 84 mm con los tres relés,
borne de 230 V, NodeMCU sobre zócalos y pantalla DWIN 4" táctil; firmware
`firmware/thermostat_rev_b/` y caja v9. Ver [REV_B.md](REV_B.md). Lo que sigue
describe la Rev A, que queda congelada.

La placa nueva es exclusivamente de control a 5/3,3 V. Maneja tres relés externos
Hongfa HF115F (bobina 5 V, diodo en cada bobina) mediante BC547B: D7 compresor, D8 calefacción y D6 ventilador. Los relés y todas las
protecciones/cables de 240 V permanecen fuera del PCB.

Estado: placa universal Rev A de 100 × 100 mm ruteada y Gerbers exportados;
validador geométrico: 0 infracciones sobre 25 redes y 103 pads. **No pagar aún**:
faltan impresión 1:1 con piezas reales, comprobar la fijación en la caja,
segunda revisión y
comprobación del ZIP en el visor/DFM de PCBWay. El banco a 5 V bloquea la
instalación, no el pedido de la placa desnuda. Seguir
[PASOS_HASTA_PEDIDO.md](PASOS_HASTA_PEDIDO.md) y
[PINOUT_Y_MONTAJE.md](PINOUT_Y_MONTAJE.md).

La placa tiene cuatro taladros **no metalizados Ø3,0 mm**, centros a 5 mm de
cada borde (patrón 90 × 90 mm). Comprobar caja y tornillos reales: Ø3,0 mm
nominal es ajustado para M3.

La Rev A usa una huella específica BC547B **C-B-E en línea a 2,54 mm**; pedir
la versión Diotec en cinta indicada en la BOM, no la variante BK de 1,27 mm.
Hay dos opciones de pedido para el **mismo Gerber**: PCB desnuda con componentes
propios o PCBWay turn-key THT con BOM e instrucciones de ensamblaje en
`pcbway/thermostat_universal_rev_a/`. NodeMCU, OLED, RTC, DHT y mandos
permanecen externos en ambas.
El firmware compila para `esp8266:esp8266:nodemcuv2` con core 3.1.2 y las
librerías DHT 1.4.7, RTClib 2.1.4 y U8g2 2.36.19; no se ha flasheado ni
probado con el NodeMCU real.

## Firmware

Copiar `Secrets.h.example` a `Secrets.h` y completar WiFi si se desea. Sin
credenciales o sin red, el control local sigue funcionando.

Endpoints:

- `/temp?temp=22.5` — rango 15–30 °C;
- `/hot?hot=true&confirm=true` o `/heating?heating=true&confirm=true`;
- `/cold?cold=true&confirm=true` o
  `/compressor?compressor=true&confirm=true`;
- `/fan?fan=true&confirm=true`;
- `/auto?auto=true`.

Para apagar una salida forzada no se requiere `confirm=true`. El interruptor
físico OFF apaga inmediatamente todas las salidas y rechaza órdenes de actuación.

## Archivos

- `thermostat.ino`: firmware.
- `thermostat_universal.fzz`: diseño Fritzing vigente, SELV, ruteado.
- `build_universal_fzz.py`: generación reproducible del `.fzz` vigente.
- `validate_universal_pcb.py`: comprobación geométrica y de continuidad.
- `VERIFICACION_HUELLAS.md`: contraste documental con fichas de fabricante;
  identifica variantes JST con tetón incompatibles con la Rev A.
- `pcbway/thermostat_universal_rev_a/`: Gerbers, taladros, BOM y vista de control.
- `sketch_pcb.fzz` y `repair_thermostat_fzz.py`: diseño y reparación históricos;
  no son los ficheros que se deben enviar a fabricar.
- `PASOS_HASTA_PEDIDO.md`: documento canónico de cableado, cálculos y proceso.
- `PLAN_PLACA_UNIVERSAL_EXTERNA.md`: placa con módulos externos y variantes de montaje.
- `checklist.md`: distingue fabricación de puesta en servicio.
