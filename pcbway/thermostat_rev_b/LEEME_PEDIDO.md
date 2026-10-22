# Rev B – instrucciones de pedido (PCBWay o JLCPCB)

**No pedir hasta completar la lista «Pendiente antes de pedir» de `REV_B.md`.**

## Placa (igual en los dos fabricantes)

- Fichero: `thermostat_rev_b_GERBER.zip` (Gerber RS-274X + Excellon, exportado con Fritzing 1.0.1).
- 84 × 84 mm, 2 capas, FR-4 TG130–150, 1,6 mm, cobre exterior 1 oz (2 oz opcional: más margen en las pistas de 230 V).
- Máscara verde, serigrafía blanca, HASL sin plomo; taladro mínimo 0,6 mm (vías), pista/separación mínima 0,61/0,24 mm.
- 4 taladros sin metalizar Ø3,2 mm; 134 metalizados (107 pads + 27 vías).
- Montaje solo por la cara superior: 21 SMD + 9 THT a máquina o a mano según el fabricante.

## PCBWay (turn-key)

- BOM: `pcbway/BOM_PCBWAY.csv`; centroides: `pcbway/CENTROID_PCBWAY.csv` (mm, origen abajo a la izquierda).
- Todas las piezas llevan fabricante y referencia: PCBWay puede comprar la borna Phoenix 1715747 y el fusible Littelfuse 37416300000.
- U1 (zócalos de la NodeMCU) va marcado como **no montar**: se sueldan a mano en las filas que correspondan al módulo real.

## JLCPCB (PCBA estándar)

- BOM: `jlcpcb/BOM_JLCPCB.csv`; CPL: `jlcpcb/CPL_JLCPCB.csv`.
- Sin código LCSC y fuera del CPL, para soldar a mano: **J20** (borna 4P 5,08 mm de 230 V), **F2** (fusible TR5 T6,3 A) y **U1** (2 zócalos 1×15).
- Piezas «extended» (cobran carga por referencia): relé C9225, BC817-40 C2982853, PTC C142746, condensador C2886738, JST y borna J1.
- Revisar en la vista previa la rotación de D1–D3 (180°, banda del cátodo hacia la derecha, hacia +5 V) y de Q1–Q3 (SOT-23 con B y E a la izquierda).

## Al recibir las placas

1. Medir con el polímetro que no hay continuidad entre L/COMP/CALOR/VENT y cualquier pin SELV (J1–J5, U1).
2. Comprobar cada relé antes de soldar: COM–NC cerrado en reposo y COM–NO cerrado con 5 V en la bobina.
3. Probar en banco solo con 5 V (sin 230 V): conmutación de los tres relés, arranque con la pantalla conectada y consumo.
