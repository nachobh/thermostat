# STL caja v5 (preliminar, 112 × 112 × 66,5 mm, +15 mm de mando)

Generados con `build_stl_v5.py` (cotas en `build_carcasa_v5.py`). Revisar en `visor_stl_v5.html`.

| Pieza | Archivo | Posición de impresión | Soportes |
|---|---|---|---|
| Carcasa (fondo, paredes, pilares PCB, columnas de tapa hasta z 64, repisas de las dos cubiertas, 2 orejas Ø4,5) | `carcasa.stl` | Fondo sobre la cama (140 × 112 × 64 mm) | Pequeños bajo las columnas (arrancan a z 11,5) y repisas |
| Tapa (ventana de pantalla 72,4 × 70,7, taladro pot Ø7,4, marco de la pantalla, 4 agujeros M3) | `tapa.stl` | Cara frontal sobre la cama | No |
| Cubierta SELV/230 V (partición, postes mini-placa, apoyos y esquineros del NodeMCU, retén y deflector del DHT22, 2 pasos de mazo) | `cubierta.stl` | Plana sobre la cama | No |
| Cubierta de la bolsa de 230 V | `cubierta_bolsa.stl` | Plana | No |
| Las cuatro en su sitio | `ensamblado.stl` | Solo revisión | — |

- Estancas y **sin interferencias** entre piezas ni con los volúmenes de PCB + componentes, NodeMCU (placa, ESP-12, USB, regletas y conectores), DHT22, pantalla, potenciómetro y mini-placa + relés.
- Pantalla supuesta (90,6 × 86,1 × 13,4; ventana 72,4 × 70,7 centrada en y = +7). **Confirmar con el plano mecánico de DWIN**; si cambian la posición del área activa o los orificios, solo se reimprime la tapa.
- Material: la bolsa de 230 V debería ser autoextinguible (V-0); PLA no vale. Tornillería como en v4 (4 × M3 × 12 tapa; M3 PCB; M4 pared; postes mini-placa M2,5).
- Entradas de cable Ø12 en el techo (x = ±45 mm) y ventilación pasiva mínima: techo 6 cm², laterales 1 cm², DHT 2 cm².
