# v7 (preliminar): pantalla 4:3 de ~145 × 110 mm, sin potenciómetro – 2026-10-21

## Pantalla elegida
**DWIN 5,7" 640×480 (4:3), táctil capacitiva, T5L0/DGUS II.** Contorno ≈ **144,8 × 110,2 mm**, grosor 17,1–18,9 mm según variante, área activa **115,2 × 86,4 mm (≈ 100 cm²)**. Es la pantalla con contorno más parecido a los 140–150 × 110–120 mm pedidos que he encontrado; las 4:3 de 5,6" tienen el mismo formato.

Fuentes (listados de distribuidor, no hoja de DWIN): [DMG64480T057_01WTC](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg64480t057_01wtc-dwin-5-7-640x480-smart-lcd-tft-display), [DMG64480K057_03WN](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg64480k057_03wn-dwin-5-7-640x480-smart-lcd-tft-display), [DMG64480T056_01WTC (5,6")](https://unisystem.com/product/displays-lcd-tft/smart-displays/dmg64480t056_01wtc-dwin-5-6-640x480-smart-lcd-tft-display).

## Hay que confirmar antes de comprar
- **Variante con UART a nivel TTL y táctil capacitivo** (p. ej. T057_01WTC). Un listado de la K057_03WN indica "RS232": si el puerto es RS232 de verdad (± 12 V) **destruye los GPIO del ESP8266**; hace falta TTL 3,3 V o un convertidor (MAX3232).
- Plano mecánico (grosor exacto 17,1/18,7/18,9 mm, orificios, posición del área activa, conector) y consumo a 5 V. El diseño supone 18,9 mm y área activa centrada.
- Alimentación: cargador de 5 V ≥ 2 A y bornero común para NodeMCU, PCB (J1) y pantalla (ver `PANTALLA_V6.md`).

## Caja v7: 161 × 122 × 49,8 mm, frontal liso
- **Sin mando; A0 libre; `-DUSE_POT=0`** (ver `PANTALLA_V6.md`).
- **PCB de 100 × 100 a la izquierda** y una **columna derecha de 49,5 mm** con: arriba la bolsa de 230 V (3 relés HF115F girados en vertical, bornas en horizontal, mini-placa de 48 × 48 mm) y abajo el NodeMCU en vertical (invertido, USB hacia abajo) con el DHT22 a su derecha y un deflector entre ambos.
- Todo queda en una sola capa a ≤ 25,6 mm de la pared; la pantalla (z 28,4–47,3) va delante. Si el NodeMCU se suelda en lugar de usar conectores Dupont, se ganan ~ 9 mm de altura interna.
- Los 4 tornillos de la tapa están en las esquinas, fuera del contorno de la pantalla (columnas r 2,5 en x = ±76, y = ±56,5).

| Versión | Caja | Volumen | Pantalla (área activa) |
|---|---|---|---|
| v5 (DWIN 4" + pot) | 112 × 112 × 66,5 (+15) | 834 cm³ | 50 cm² |
| v6 (DWIN 7", sin pot) | 206 × 120 × 44,5 | 1100 cm³ | 132 cm² |
| **v7 (DWIN 5,7", sin pot)** | **161 × 122 × 49,8** | **978 cm³** | **100 cm²** |

El contorno exterior es el de la pantalla + ≈ 16 × 12 mm de pared y holgura; no se puede bajar más con la PCB actual (el hueco lateral de 49,5 mm lo fija el NodeMCU + DHT22 en una columna).

## Archivos
`render_v7*.png`, `render_v7.html`, `esquema_v7.png`, `stl_v7/` (+ `visor_stl_v7.html`). Tres piezas, estancas y sin interferencias con PCB + componentes, NodeMCU, DHT22, pantalla, mini-placa, relés y bornas.
