# PCBWay — thermostat universal Rev A

**No pagar aún sin la comprobación física 1:1 y segunda revisión.**
El archivo para fabricar es `thermostat_universal_rev_a_GERBER.zip`; el `.fzz`
es la fuente editable, no se envía como Gerber. Hay dos opciones para **la misma
PCB**: A, placa desnuda según `BOM_MONTAJE_MANUAL.csv`; B, PCBWay suministra y
monta 38 componentes THT según `BOM_PCBWAY_TURNKEY.csv` e
`INSTRUCCIONES_PCBA_TURNKEY.md`. Pedir 2 capas, 100 × 100 mm, FR-4 1,6 mm,
cobre 1 oz y HASL o equivalente. Sólo baja
tensión SELV. Los tres SSR y toda la red de 240 V permanecen externos.

Contenido previsto del ZIP: cobre superior/inferior `.gtl/.gbl`, máscaras
`.gts/.gbs`, serigrafías `.gto/.gbo`, contorno `.gm1` y taladro Excellon
`_drill.txt`. El archivo `.xy` exportado por Fritzing **no se debe enviar
directamente**: marca F1 como SMT aunque es THT. La opción B usa
`COLOCACION_THT_REFERENCIA.csv` sólo como ayuda de posición; PCBWay permite
omitir THT del centroid. No hay SMD ni capa de pasta.

Validación automatizada: `python3 build_universal_fzz.py` generó 25 redes;
`python3 validate_universal_pcb.py` verificó continuidad, separación cobre-cobre
≥0,20 mm y bordes: 41 componentes, 103 pads, 1022 segmentos, 18 vías, 0
infracciones. Gerbers exportados con Fritzing 1.0.1 y abiertos en `gerbv`.
El Excellon contiene 121 taladros metalizados (103 pads y 18 vías) y cuatro
**NPTH Ø3,0 mm** en centros (5,5), (95,5), (5,95), (95,95) mm.
Contorno: 100 × 100 mm. Estas comprobaciones no prueban la orientación de
componentes reales ni sustituyen el DFM del fabricante.
`python3 package_pcbway.py` comprueba además que las 41 referencias de la BOM
estén exactamente una vez, que el `.fzz` copiado sea idéntico al original, que
ninguna capa preceda al `.fzz` y que el ZIP reproduzca las ocho capas byte a byte.
La separación mínima medida de 0,237 mm supera la recomendación de PCBWay de
0,15 mm para ahorrar costes en PCB estándar; aun así, comprobar la aceptación
del visor/DFM del pedido. [Fuente: tolerancias PCBWay](https://www.pcbway.com/pcb_prototype/PCB_Manufacturing_tolerances.html).

Antes del pedido: imprimir el PCB al 100 %, presentar J1–J10 JST-XH,
J11–J13 Phoenix MKDS 1715721, F1 RXEF030, BC547B y pasivas; verificar
particularmente C-B-E y polaridad de electrolíticos, mazos y mando D0/3V3.
Confirmar por segunda persona el [pinout](../../PINOUT_Y_MONTAJE.md), abrir el
ZIP en el visor de PCBWay y comparar sus ocho capas/taladros con el `.fzz`.
Confirmar que la caja admite 100 × 100 mm, centros de fijación 90 × 90 mm y
la altura de los conectores. Presentar el tornillo real en la plantilla:
Ø3,0 mm nominal puede ser ajustado para M3.
El flasheo y las pruebas eléctricas de banco/potencia bloquean la puesta en
servicio, no el pedido de la PCB desnuda; las huellas y la fijación sí deben
resolverse antes de fabricar. Después del montaje, probar exclusivamente con
5 V antes de acercarse a la instalación de red. La guía completa está en
[PASOS_HASTA_PEDIDO.md](../../PASOS_HASTA_PEDIDO.md).

`PLANTILLA_1_A_1.pdf` contiene contorno, serigrafía y taladros para esa prueba
física. Imprimir con **«tamaño real / 100 %»**, sin «ajustar a página», y medir
con regla: el contorno debe ser 100 × 100 mm. El PDF no se envía a PCBWay.
