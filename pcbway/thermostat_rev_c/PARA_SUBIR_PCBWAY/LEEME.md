# Rev C → PCBWay: qué subir y cómo rellenar el formulario

Pedir **presupuesto**, no pagar todavía. Pagar cuando PCBWay dé el precio y confirme las dos huellas: la del relé y la del conector J6.

## Ficheros de esta carpeta

| Fichero | Dónde va en PCBWay |
|---|---|
| `thermostat_rev_c_GERBER.zip` | «Upload Gerber» |
| `BOM_PCBWAY_REV_C.xlsx` | «Upload BOM» (la `.csv` es la misma, por si la piden en ese formato) |
| `CENTROID_PCBWAY_REV_C.xlsx` | «Upload Centroid / Pick and place» |
| `ASSEMBLY_DRAWING_REV_C.pdf` | «Other files» o adjunto al mensaje |
| `MENSAJE_PCBWAY.txt` | Texto para el campo de notas («Remarks») y para responder a Lynne en el hilo |

## Formulario de montaje (PCB Assembly → Turnkey)

| Campo | Valor |
|---|---|
| Service | **Turnkey** (ellos compran todas las piezas) |
| Board type | Single pieces |
| Assembly side(s) | **Bottom side** para SMT; las THT van arriba. Si el formulario solo deja elegir «Top / Bottom / Both», marca **Bottom** y aclara en notas que las THT están arriba (ya lo dice el mensaje) |
| Quantity | **2** |
| Contains sensitive components/parts | No |
| Number of unique parts | **14** (líneas de la BOM) |
| Number of SMD parts | **20** |
| Number of BGA/QFP parts | 0 |
| Number of through-hole parts | **11** (3 relés, J20, J1, F2, C1, J3, J5 y 2 zócalos) |

## Formulario de la placa

| Campo | Valor |
|---|---|
| Size | **84 × 84 mm** |
| Quantity | La que pida como mínimo (suele ser 5); se montan 2 |
| Layers | 2 |
| Material | FR-4, TG130–140 |
| Thickness | 1,6 mm |
| Min track/spacing | 6/6 mil (o la opción estándar). El diseño usa como mínimo 0,25 mm de pista y 0,20 mm de separación (en los pines del FPC) |
| Min hole size | 0,3 mm o la estándar (las vías son de 0,6 mm) |
| Solder mask | Green |
| Silkscreen | White |
| Surface finish | HASL lead free |
| Via process | Tenting vias |
| Finished copper | 1 oz (2 oz es opcional: más margen en las pistas de 230 V, pero sube el precio) |
| Gold fingers / castellated / edge plating | No |
| Product No. (número de pedido serigrafiado) | Pedir que no lo pongan en la zona de 230 V; mejor en la cara inferior, mitad de abajo (ya lo dice el mensaje) |

## Después

- Cuando llegue el presupuesto, pégamelo y lo revisamos juntos antes de pagar: precio, piezas sustituidas y preguntas de ingeniería.
- Si preguntan por la orientación de alguna pieza, el PDF de montaje y la serigrafía de las dos caras son la referencia.

## Variante para la oferta de montaje de 29 $ (2026-10-22)

La oferta exige como máximo **100 soldaduras THT por pedido** y se aplica a **un solo pedido** del carrito a la vez.
Con los zócalos de la NodeMCU serían 72 × 2 = 144, así que **U1 no se monta**: lo sueldas tú (2 tiras hembra 1×15 de 2,54 mm por placa).

| Campo / fichero | Valor |
|---|---|
| BOM | `BOM_PCBWAY_REV_C_SIN_U1.xlsx` (13 líneas) |
| Centroid | `CENTROID_PCBWAY_REV_C_SIN_U1.xlsx` |
| Número de diferentes componentes | **13** |
| Componentes SMD | **20** |
| Componentes BGA/QFP | 0 |
| Pasantes | **9** (42 soldaduras por placa, 84 en total) |
| Notas de montaje (< 600 caracteres) | ver abajo |

```
SMT on BOTTOM side only (20 SMD incl. J6 FPC AFC07-S50ECA-00). THT on top: 3 relays, 2 terminals, fuse, cap, 2 JST (42 joints/board, 84 total). U1 sockets NOT assembled/supplied. Please check: 1) HF115F/005-1ZS3 footprint: COM middle column, NC next to coil, NO far end. 2) AFC07: upper contact, bottom side, opening to top edge. 230VAC above dashed line: keep mask/clearances. Propose substitutes before buying. $29 SMT offer please.
```
