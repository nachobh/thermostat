# v6 (preliminar): solo pantalla, sin potenciómetro, pantalla más grande – 2026-10-21

## Qué cambia respecto a v5
- **Sin potenciómetro ni mando:** frontal liso con la pantalla. A0 queda libre; J9 sin usar. Firmware: `USE_POT 0` (ver abajo).
- **Pantalla DWIN 7" 800×480 táctil** en lugar de la 4" 480×480: área activa 154,1 × 85,9 mm = **132 cm²** (v5: 50 cm²; v1 con 2 OLED: ≈ 12 cm²).
- **Todo en una sola capa detrás de la pantalla:** PCB SELV a la izquierda; a la derecha NodeMCU (vertical, invertido, USB hacia abajo) y DHT22 abajo, bolsa de 230 V arriba con los 3 relés girados. La profundidad baja de 66,5 a 44,5 mm.

## Tamaños
| Versión | Caja | Volumen | Superficie de pantalla |
|---|---|---|---|
| v4 (2 OLED + pot) | 112 × 112 × 56,5 | 709 cm³ | ≈ 12 cm² |
| v5 (DWIN 4" + pot) | 112 × 112 × 66,5 (+15 mando) | 834 cm³ | 50 cm² |
| **v6 (DWIN 7", sin pot)** | **206 × 120 × 44,5** | **1100 cm³** | **132 cm²** |

Quitar el potenciómetro **no reduce la huella** con la PCB actual: la placa de 100 × 100 mm ya fija un mínimo de ≈ 106 × 106 mm. Para una caja realmente más pequeña haría falta rediseñar la PCB (más compacta); no es necesario para la v6.

## Pantallas DWIN consideradas
| Modelo | Contorno | Área activa | Interfaz | Nota |
|---|---|---|---|---|
| DMG48480 4" 480×480 | 90,6 × 86,1 × 12–13,4 | 71,9 × 70,2 | UART | v5 |
| DMG80480C050 5" 800×480 (04WTC) | 143,5 × 80,9 × 15,6 | 108,0 × 64,8 | UART/RS232, 4,5–5,5 V | Ancho 143 mm: no cabe la PCB al lado; habría que apilar como en v5 |
| **DMG80480C070 7" 800×480** | **190,5 × 105,4 × 13,4 (03WTC) / 13,6 (04WTC)** | **154,1 × 85,9** | 03WTC listado como RGB, 04WTC como UART | v6; **hay que pedir la variante UART (04WTC)** |

Fuentes: [DWIN 7" DMG80480C070_03WTC](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg80480c070_03wtc-dwin-7-800x480-smart-lcd-tft-display), [DMG80480C070_04WTC](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg80480c070_04wtc-dwin-7-800x480-smart-lcd-tft-display), [DWIN 5" 03WN](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg80480c050_03wn-dwin-5-800x480-smart-lcd-tft-display), [DWIN 5" 04WTC](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg80480c050_04wtc-dwin-5-800x480-smart-lcd-tft-display).

## Pendiente de confirmar (no está en los listados)
- Plano mecánico del 7" UART (contorno exacto de la 04WTC, posición del área activa, orificios, conector) y **consumo** a 5 V. Un 7" suele pedir bastante más que un 4": prever un **cargador de 5 V ≥ 2 A** (el diseño actual supone 1 A).
- Alimentación: la pantalla no debe colgar de la pata Vin del NodeMCU si éste se alimenta por su micro-USB (conector y diodo limitados). Lo más seguro es alimentar NodeMCU, PCB (J1) y pantalla desde un mismo bornero de 5 V del cargador y usar el micro-USB solo para programar.
- Cableado de datos: igual que v5 (TX pantalla → D3/GPIO0, RX pantalla ← D4/GPIO2, por J10; boot pins, probar en banco).

## Firmware
- `thermostat.ino` ya tiene `USE_POT` (por defecto 1, sin cambio de comportamiento). Para la v6 compilar con `-DUSE_POT=0`: no lee A0, la consigna arranca en `DEFAULT_SETPOINT_C` (21,0 °C) y solo cambia por `/temp` (o por la pantalla, cuando se programe). **No compilado en este equipo.**
- Sigue pendiente reescribir la parte de OLED y pulsadores por el protocolo UART de DWIN y diseñar la interfaz con DGUS Tool.
