# Opción B: PCBWay suministra y monta la PCB de control

Esta opción usa **exactamente los mismos ocho Gerber/Excellon** que la opción A
de montaje manual. No hay una segunda placa ni diferencias eléctricas que
puedan provocar dos tiradas incompatibles. Solicitar **PCB + montaje THT,
aprovisionamiento turn-key**, sólo por la cara superior; no solicitar SMT.

Archivos para cotizar: `thermostat_universal_rev_a_GERBER.zip`,
`BOM_PCBWAY_TURNKEY.csv`, `COLOCACION_THT_REFERENCIA.csv`,
`VERIFICACION_TOP.png`, `PLANTILLA_1_A_1.pdf` y esta instrucción.
La tabla de colocación es **referencia THT**, no programa automático de
pick-and-place: el fichero XY bruto de Fritzing marca F1 erróneamente como
SMT y no debe enviarse. PCBWay indica que las referencias THT pueden omitirse
del centroid; no hay componentes SMT ni capa de pasta en este diseño.

## Población y sustituciones

- Montar las 38 referencias de las 14 líneas de `BOM_PCBWAY_TURNKEY.csv`.
  **NO MONTAR R7, R8 ni R9**: son pull-ups opcionales que se deciden tras medir
  los módulos externos. Dejar sus pads accesibles.
- R10–R14 son cinco puentes **obligatorios** de 0 Ω; omitirlos rompe redes.
- J1/J8/J9 = JST B3B-XH-A, J2–J7 = B4B-XH-A, J10 = B5B-XH-A. Sólo versiones
  **sin boss**; no aceptar `-AM` ni cambios de familia/paso.
- J11–J13 = Phoenix Contact MKDS 1,5/2-5,08, pedido 1715721. Son conectores
  exclusivos de entrada SELV de los SSR externos; nunca llevar 240 V aquí.
- F1 = Littelfuse RXEF030/RF2565-000; comprobar que sea radial THT con paso
  5,08 mm. Fritzing lo etiqueta SMT en su XY bruto, pero la huella tiene dos
  taladros metalizados.
- Q1–Q3 = Diotec BC547B con patillas **C-B-E en línea a 2,54 mm**. No aceptar
  variante BK de 1,27 mm ni transistor con orden E-B-C. La cara plana debe
  coincidir con la línea recta de serigrafía; comprobar C/B/E con la ficha y
  la pieza recibida antes de soldar.
- C8 = 100 µF y C10 = 47 µF, ambos radiales Ø≤5 mm, paso 2,54 mm, ≥10 V;
  positivo en el pad `+` serigrafiado. Confirmar dimensiones de la referencia
  propuesta por PCBWay antes de aprobar sustitución.
- Las resistencias axiales de 1 kΩ, 10 kΩ y 0 Ω deben tener cuerpo/terminales
  formables a paso 10,16 mm. Los cerámicos de 100 nF son radiales paso 2,54 mm.
  Valores genéricos no autorizan cambiar paso, tensión ni tamaño físico.

PCBWay puede suministrar las piezas según cotización, pero la disponibilidad,
referencias sustitutivas, precio y orientación final **requieren aprobación
expresa del comprador**. No sustituir silenciosamente. Solicitar foto de una
unidad montada, incluyendo C8/C10, Q1–Q3, J1–J13 y los puentes R10–R14.

## Lo que PCBWay no monta en esta placa

NodeMCU, dos OLED, RTC, DHT, potenciómetro, mandos, cargador USB, mazos JST y
los tres SSR quedan externos según la arquitectura acordada. Se pueden pedir
como piezas/mazos separados sólo mediante cotización adicional y con el
pinout de `../../PINOUT_Y_MONTAJE.md`; no forman parte de la BOM PCBA. La caja,
el circuito de 240 V y sus protecciones tampoco forman parte de esta placa.

## Comprobaciones que siguen abiertas

1. Presentar piezas reales sobre `PLANTILLA_1_A_1.pdf` impresa al 100 %.
2. Confirmar que la caja acepta 100 × 100 mm y cuatro centros de fijación a
   90 × 90 mm. Los agujeros son NPTH Ø3,0 mm, a 5 mm de cada borde;
   comprobar tornillería, altura de bornas y salida de cables.
3. Obtener una segunda revisión de pinout, huellas, polaridad y Gerbers.
4. Pasar el visor/DFM de PCBWay y recibir aprobación de montaje/sourcing THT.

No pagar hasta cerrar 1–4. El ensamblaje no incluye flasheo ni prueba funcional
del termostato; probar primero a 5 V y sin red de 240 V.
