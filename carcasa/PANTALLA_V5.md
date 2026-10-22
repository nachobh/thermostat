# Pantalla grande para el termostato (v5, preliminar) – 2026-10-21

Objetivo: sustituir los 2 OLED por una sola pantalla de casi 10 × 10 cm, con 4 hilos de datos como máximo + 2 de alimentación, sobre la PCB Rev A ya pedida.

## Restricción de la PCB y del ESP8266
La PCB no lleva ningún conector SPI: D5 (SCK) es el DHT, D7 (MOSI) el compresor, D6 el ventilador, D8 la calefacción, D1/D2 son I²C (RTC), D0 el interruptor de habilitación y A0 el potenciómetro. Solo D3 y D4 (pulsadores MENU/SELECT en J10) quedan libres **si la pantalla es táctil y sustituye a los pulsadores**. Una pantalla SPI (4 señales + RST/BUSY) no cabe sin rediseñar la PCB.

## Candidatas
| Pantalla | Tamaño módulo | Interfaz | ¿Encaja? |
|---|---|---|---|
| **DWIN DMG48480 4" 480×480 (T5L)** | ≈ 90,6 × 86,1 × 12–13,4 mm; área activa ≈ 71,9 × 70,2 | UART (5 V, GND, TX, RX) + táctil | **Sí**: casi cuadrada, 4 hilos, 2 GPIO (D3/D4), no necesita RAM del ESP8266 |
| Nextion NX4827K043 4,3" 480×272 | 120 × 74 × 6,2 mm (activa 105,5 × 67,2) | UART (4 hilos), resistiva, 250 mA a 5 V | Sí, pero no es cuadrada: queda ~46 mm sin usar en vertical |
| Waveshare 4,2" e-paper 400×300 | 93,5 × 78,5 mm (activa 84,8 × 63,6) | SPI 3/4 hilos + RST + BUSY (8 hilos) | No sin GPIO extra; además refresco lento |
| Paneles cuadrados 4" 480×480 ST7701 (RGB) | ≈ 78 × 82 mm | RGB paralelo; SPI solo para configurar | No: el ESP8266 no tiene RGB ni RAM |

Fuentes: [DWIN DMG48480C040_03WN](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg48480c040_03wn-dwin-4-0-480x480-smart-lcd-tft-display) y [DMG48480T040_01WN](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg48480t040_01wn-dwin-4-0-480x480-smart-lcd-tft-display) (dimensiones), [Nextion NX4827K043](https://www.robotshop.com/products/nx4827k043-nextion-43-enhanced-series-hmi-resistive-touch-display), [Waveshare 4,2" e-paper](https://waveshare.com/pico-epaper-4.2.htm), [New Haven 4" RGB](https://newhavendisplay.com/it/4-0-inch-square-ips-tft-with-rgb-interface).

## Lo que NO he podido confirmar (hacerlo antes de comprar)
- El modelo exacto (táctil capacitivo, `…_03WTC`, o sin táctil), su plano mecánico (orificios de fijación, posición del área activa) y su corriente. Los datos de la caja salen de listados de distribuidores, no de la hoja de DWIN.
- Niveles lógicos del UART (se espera 3,3 V TTL) y alimentación (5 V). Medir antes de conectar a GPIO0/GPIO2.

## Cableado (4 hilos) y firmware
- 5 V y GND: del pin Vin/GND del NodeMCU (no de la PCB: F1 solo cubre las bobinas). Consumo de la pantalla ≈ 0,15–0,25 A; el cargador de 1 A alcanza (NodeMCU 0,3 + 2 bobinas 0,16 + pantalla).
- TX de la pantalla → D3/GPIO0 (J10 pin 2); RX de la pantalla ← D4/GPIO2 (J10 pin 3); GND común (J10 pin 4). R16/R17 (pull-up a 3V3) quedan como pull-up de línea inactiva.
- GPIO0 y GPIO2 son pines de arranque del ESP8266: la línea TX de la pantalla debe estar en alto (reposo) durante el boot. Comprobar en banco con la pantalla ya alimentada y desconectada.
- El interruptor de habilitación (D0) y el potenciómetro (A0) se conservan.
- **El firmware actual NO maneja esta pantalla.** Hay que sustituir la parte de U8g2/OLED y los pulsadores por el protocolo UART de DWIN (tramas 0x5A 0xA5) y diseñar la interfaz con DGUS Tool. No he modificado `thermostat.ino` para esto.

## Caja v5 (112 × 112 × 66,5 mm, +15 del mando)
Capas desde la pared: PCB SELV → cubierta (z 25–27) con NodeMCU invertido y DHT22 + bolsa de 230 V (y > 15) con 3 relés HF115F → cubierta de la bolsa (z 47–48,5) → pantalla (z 50,6–64) → tapa. Pot de panel bajo la pantalla (taladro Ø7,4, mando Ø14). Sin OLED. Archivos: `render_v5*.png`, `render_v5.html`, `esquema_v5.png`, `stl_v5/`.
