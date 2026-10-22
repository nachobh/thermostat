# STL caja v4 (112 × 112 × 56,5 mm, +15 mm de mando)

Generados con `build_stl_v4.py` (cotas en `build_carcasa_v4.py`). Revisar en `visor_stl.html`.

| Pieza | Archivo | Posición de impresión | Soportes |
|---|---|---|---|
| Carcasa (fondo, paredes, pilares PCB, columnas de tapa, repisas, 2 orejas Ø4,5) | `carcasa.stl` | Fondo sobre la cama (140 × 112 × 54 mm) | Pequeños bajo las columnas de tornillo (arrancan a z = 11,5) y las repisas |
| Tapa (ventanas OLED, taladro Ø7,4 del pot, marcos de OLED/NodeMCU/DHT, deflector) | `tapa.stl` | Cara frontal sobre la cama | No |
| Bandeja de 230 V + partición + 4 postes de la mini-placa | `bandeja.stl` | Bandeja plana sobre la cama | No |
| Las tres piezas en su sitio | `ensamblado.stl` | Solo para revisar | — |

- Las tres piezas son estancas (watertight) y **sin interferencias** entre sí ni con los volúmenes de PCB + componentes, NodeMCU, 2 OLED, DHT22, potenciómetro y mini-placa + relés.
- Tornillería: 4 × M3 × 12 para la tapa (rosca directa en columnas de pilote Ø2,6; cabeza en alojamiento Ø6,4); 4 × M3 × 8 para la PCB sobre los pilares (pilote Ø2,6); 2 × M4 para pared; postes de la mini-placa con pilote Ø2,2 (M2,5).
- Material: la bolsa de 230 V debería ser autoextinguible (V-0). PLA no vale (se ablanda hacia 60 °C ni es retardante); usar PETG/ASA solo como prototipo y, para el montaje definitivo, filamento ignífugo certificado o caja comercial V-0 para la parte de red.
- Agujeros de pasacables Ø12 en el techo (x = ±45 mm) para los cables de red y de cargas: poner prensaestopas o pasacables con sujeción.
- NodeMCU, OLED y DHT: marcos de sujeción con holgura de 0,2 mm; fijar con cinta de espuma/adhesivo (el NodeMCU apoya sobre la tapa). Dimensiones del NodeMCU, OLED y DHT22 son genéricas: comprobar con calibre y reimprimir solo la tapa si difieren.
- Mini-placa de potencia: aún sin diseñar (94 × 28 mm; relés a x = −32, 0, 32 mm; bornas L/COMP/CALOR/VENT). Postes en x = ±43 mm.
