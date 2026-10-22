# STL caja v6 (preliminar, 206 × 120 × 44,5 mm, sin mando)

Generados con `build_stl_v6.py` (cotas en `build_carcasa_v6.py`). Revisar en `visor_stl_v6.html`.

| Pieza | Archivo | Posición de impresión | Soportes |
|---|---|---|---|
| Carcasa (fondo, paredes, pilares PCB, columnas de tapa, tabiques de la bolsa de 230 V, postes de la mini-placa, apoyos y esquineros del NodeMCU, retén y deflector del DHT22, 2 orejas arriba/abajo) | `carcasa.stl` | Fondo sobre la cama (206 × 148 × 42 mm: cabe en cama de 220 × 220) | No |
| Tapa (ventana 154,6 × 86,4, marco de la pantalla, 4 agujeros M3) | `tapa.stl` | Cara frontal sobre la cama | No |
| Cubierta de la bolsa de 230 V | `cubierta_bolsa.stl` | Plana | No |
| Las tres en su sitio | `ensamblado.stl` | Solo revisión | — |

- Estancas y **sin interferencias** entre piezas ni con los volúmenes de PCB + componentes, NodeMCU (placa, ESP-12, USB, regletas y conectores), DHT22, pantalla, mini-placa, relés y bornas.
- Pantalla supuesta (190,5 × 105,4 × 13,6, área activa centrada). **Confirmar con el plano mecánico de DWIN**; si cambia algo, solo se reimprime la tapa (y el marco).
- Cuatro tornillos M3 en las esquinas fuera de la pantalla (columnas en x = ±98, y = ±55 mm). Entradas de cable Ø12 en la pared derecha; USB del NodeMCU hacia abajo (hueco 12 × 9 mm).
- Material: la bolsa de 230 V debería ser autoextinguible (V-0); PLA no vale. Ventilación pasiva mínima: techo de la bolsa 5,4 cm², DHT 0,6 cm².
