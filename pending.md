# Pendientes y decisiones

Actualizado: 2026-10-01.

## Bloqueantes antes de pedir la PCB

1. Presentar a escala 1:1 JST-XH, MKDS, PTC, BC547B y pasivas reales. NodeMCU,
   OLED, RTC, DHT, potenciómetro y mandos son externos.
2. Confirmar que la caja admite PCB 100 × 100 mm y centros de tornillo 90 ×
   90 mm. La Rev A ya tiene cuatro taladros NPTH Ø3,0 mm; probar la tornillería
   elegida en una impresión 1:1 y prever altura/cables.
3. Realizar revisión independiente del pinout y Gerbers de
   `thermostat_universal.fzz`; `sketch_pcb.fzz` es histórico.
4. Subir el ZIP al visor/DFM de PCBWay y verificar capas, taladros y tamaño.

## Bloqueantes antes de poner en servicio

- Confirmar OLED 0x3C/0x3D, pull-ups I²C y rango A0 del NodeMCU real; hacer
  pruebas de banco a 5 V con la PCB poblada.
- Medir corriente de marcha y pico de arranque de calefacción, ventilador y
  compresor. El 6(3,5) A del Eberle es rating del contacto, no medición de carga.
- Validar térmicamente los tres SSR externos y cerrar fusible/disipadores.

## Decisiones ya tomadas

- Cableado fotografiado: 1/3/4/5/7; 0/2/6 sin usar.
- PCB sólo SELV; SSR-40DA, fusible/TMOV y 240 V fuera de ella.
- Alimentación con cargador USB aislado 5 V/1 A; no añadir AC/DC a la placa.
- Tres canales externos universales `+5V/CTRL-`.
- GPIO15 se mantiene en calefacción con BC547B y pull-down 10 kΩ.
- Endpoint antiguo y alias descriptivo conviven; activar exige confirmación.
- Credenciales WiFi en `Secrets.h`, no en el repositorio.
- El interruptor lógico cierra GPIO16/D0 a 3V3 para habilitar; abierto queda OFF
  por R15 pull-down y `INPUT_PULLDOWN_16`. No es seccionador de red.

## Firmware pendiente

- Compilación realizada con core ESP8266 3.1.2 y librerías DHT 1.4.7,
  RTClib 2.1.4 y U8g2 2.36.19; falta flashear y probar hardware.
- Probar el comportamiento real del límite de 300 s y decidir, tras el banco, si
  debe aplicarse sólo al rearranque del compresor. El apagado por sensor u OFF
  físico ya es inmediato.
- Los botones MENU/SELECT todavía no implementan un menú.
- El servidor web no tiene autenticación: mantenerlo sólo en la LAN.

## Piezas del prototipo ya disponibles

- El B10K sirve para A0 igual que un B100K porque ambos proporcionan el recorrido
  completo del divisor; B10K presenta además menor impedancia de fuente.
- El DHT11 comparte patillaje/protocolo con el DHT22, pero **no** es un cambio de
  firmware transparente: para montarlo hay que definir `DHTTYPE DHT11`. Su menor
  precisión hace especialmente útil la media y el filtro, aunque no sustituye la
  prueba de fallo.

## Repositorio

- La contraseña que aparecía en `thermostat.ino` era antigua/caducada; se ha
  retirado igualmente del árbol actual. Si alguna vez se publica el historial,
  asumir que seguirá recuperable en commits anteriores.
- Decidir si las fotos de WhatsApp forman parte del repositorio definitivo.
