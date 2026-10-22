# Verificación documental de huellas — Rev A

Fecha: 2026-10-01. Esta revisión compara la PCB exportada con las fichas de
fabricante. **No sustituye** presentar piezas físicas sobre la plantilla 1:1.

| Pieza de la BOM | Dato oficial | Gerber/huella Rev A | Resultado documental |
|---|---|---|---|
| JST B3B/B4B/B5B-XH-A | Paso 2,50 mm, agujero de referencia Ø0,90 mm para 3+ vías; anchos 9,9/12,4/14,9 mm | Paso 2,50 mm, taladro Ø0,90 mm, cuerpo 9,9/12,4/14,9 mm | Coincide |
| Phoenix Contact MKDS 1715721 | Paso 5,08 mm; taladro Ø1,30 mm; ancho 10,16 mm, longitud 9,8 mm | Paso 5,08 mm; taladro Ø1,30 mm; cuerpo 10,16 × 9,8 mm | Coincide |
| Littelfuse RXEF030/RF2565-000 | Separación de patillas nominal 5,05 ±0,75 mm; Ihold 0,30 A a 20 °C | Paso 5,08 mm, taladro Fritzing ~0,89 mm | Coincide en paso; presentar pieza para confirmar taladro/cuerpo |
| Diotec BC547B TO-92 en cinta | C=1, B=2, E=3; paso 2,54 mm (la variante BK usa 1,27 mm) | Tres pads en línea C-B-E, paso 2,54 mm, taladro Ø0,90 mm, cara plana marcada | Coincide documentalmente; presentar pieza real |

**Importante JST:** la serie `B...-XH-A` indicada en la BOM es la versión
**sin tetón de centrado**. Las variantes `B...-XH-AM` llevan boss y necesitan
un agujero mecánico adicional que esta placa **no tiene**. Pedir exactamente
la referencia sin `M`; si el vendedor entrega `-AM`, no soldarla ni forzarla.

**PTC:** el Ihold publicado baja con la temperatura. La ficha muestra 0,12 A
a 85 °C para RXEF030, todavía por encima de los 75 mA máximos supuestos para
tres entradas SSR de 25 mA, pero la corriente real debe medirse. F1 sólo
protege la rama de entradas SSR a 5 V, no el NodeMCU ni 240 V.

La Rev A usa ahora una huella BC547B **en línea** creada para la versión
Diotec de paso 2,54 mm. Eliminar la antigua huella triangular reduce el riesgo
de montar mal una patilla. Pedir la versión en cinta; si sólo se dispone de la
variante BK de paso 1,27 mm u otro fabricante, presentar la pieza y verificar
si los terminales se pueden formar sin tensión mecánica. No sustituir por un
TO-92 con orden E-B-C.

Fuentes de fabricante:

- [JST XH, montaje PCB y tabla de variantes con/sin boss](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf)
- [Phoenix Contact 1715721, dimensiones y taladro](https://www.phoenixcontact.com/en-gb/products/printed-circuit-board-terminal-mkds-15-2-508-1715721)
- [Littelfuse RXEF, RXEF030 y derating](https://www.littelfuse.com/assetdocs/littelfuse_ptc_radial_leaded_rxef_datasheet?assetguid=e9a7b6b3-79ce-478c-a39a-0a70ee48ccec)
- [Diotec BC546–BC549, pinout y encapsulado](https://diotec.com/request/datasheet/bc546.pdf)
