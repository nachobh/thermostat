# STL caja v8 (preliminar, 144,8 × 110,2 × 50 mm de carcasa; con la pantalla 68,9 mm)

Generados con `build_stl_v8.py` (cotas en `build_carcasa_v8.py`). Revisar en `visor_stl_v8.html`.

| Pieza | Archivo | Posición de impresión | Soportes |
|---|---|---|---|
| Carcasa (fondo, paredes de 2,5 mm con pestaña de pegado, pilares PCB, repisas, costillas, apoyos y esquineros del NodeMCU, retén y deflector del DHT22, 2 orejas arriba/abajo) | `carcasa.stl` | Fondo sobre la cama (144,8 × 136,2 × 50 mm) | No (la pestaña superior es un voladizo de 4 mm) |
| Cubierta de 230 V (bandeja + tabique derecho + postes de la mini-placa) | `cubierta.stl` | Bandeja plana sobre la cama | No |
| Tapa de la cubierta | `tapa_cubierta.stl` | Plana | No |
| Todo en su sitio | `ensamblado.stl` | Solo revisión | — |

- La cubierta y su tapa se apoyan en repisas y costillas de la carcasa y se fijan por fricción/pegado; la pantalla se pega sobre la pestaña con cinta VHB.
- Paso J11–J13 (14 × 40 mm) en la bandeja para las bobinas; entradas de cable Ø12 en la pared izquierda (y = 20 y 40 mm); USB del NodeMCU hacia abajo; hueco de ventilación del DHT22 (7 × 20 mm) en la pared derecha.
- La zona de 230 V debería ser autoextinguible (V-0); PLA no vale.
