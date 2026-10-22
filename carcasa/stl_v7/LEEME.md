# STL caja v7 (preliminar, 161 × 122 × 49,8 mm)

Generados con `build_stl_v7.py` (cotas en `build_carcasa_v7.py`). Revisar en `visor_stl_v7.html`.

| Pieza | Archivo | Posición de impresión | Soportes |
|---|---|---|---|
| Carcasa (fondo, paredes, pilares PCB, columnas de tapa, tabiques de la bolsa de 230 V, postes de la mini-placa, apoyos y esquineros del NodeMCU, retén y deflector del DHT22, 2 orejas arriba/abajo) | `carcasa.stl` | Fondo sobre la cama (161 × 148 × 47,3 mm) | No |
| Tapa (ventana 115,7 × 86,9, marco de la pantalla, 4 agujeros M3) | `tapa.stl` | Cara frontal sobre la cama | No |
| Cubierta de la bolsa de 230 V | `cubierta_bolsa.stl` | Plana | No |
| Las tres en su sitio | `ensamblado.stl` | Solo revisión | — |

- Pantalla supuesta (144,8 × 110,2 × 18,9, área activa centrada): **confirmar con el plano de DWIN**; si cambia, solo se reimprime la tapa.
- Entradas de cable Ø12 en la pared derecha (y = 15 y 38 mm); USB del NodeMCU hacia abajo (hueco 12 × 9 mm).
- La bolsa de 230 V debería ser autoextinguible (V-0); PLA no vale. Ventilación pasiva mínima: techo de la bolsa 3,6 cm², DHT 0,6 cm².
