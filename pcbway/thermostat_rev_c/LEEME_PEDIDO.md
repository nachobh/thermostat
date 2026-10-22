# Rev C – instrucciones de pedido (PCBWay o JLCPCB)

**No pedir hasta completar «Pendiente antes de pedir» en `REV_C.md`.** Las medidas del FPC salen del modelo 3D de DWIN.

## Placa (igual en los dos fabricantes)

- Fichero: `thermostat_rev_c_GERBER.zip`. Incluye Gerber RS-274X, Excellon y la pasta inferior (la única); la pasta y la serigrafía inferiores las añade `package_rev_b.py`.
- 84 × 84 mm, 2 capas, FR-4, 1,6 mm, 1 oz (2 oz opcional para las pistas de 230 V), máscara verde, serigrafía blanca, HASL sin plomo.
- Pista/separación mínima: 0,25/0,20 mm en los pines del FPC de 0,5 mm. El resto es más holgado. Taladro mínimo 0,6 mm.
- 4 taladros sin metalizar Ø3,2 mm; 91 metalizados (72 pads + 19 vías).
- **SMT en una sola cara, la inferior:** las 19 SMD más J6, el conector FPC AFC07-S50ECA-00. No hay pasta en la cara superior.
- **Piezas de patillas en la superior:** relés, bornas, JST, zócalos y C1.

## PCBWay (turn-key)

- BOM `pcbway/BOM_PCBWAY.csv` y centroides `pcbway/CENTROID_PCBWAY.csv` (todas las SMD con capa «Bottom»).
- U1 = 2 zócalos 1×15 en las dos filas de la huella (NodeMCU Amica, 22,86 mm entre filas).
- J6: cara inferior, con la boca del conector hacia el borde superior de la placa (hacia la zona de 230 V), como en la serigrafía inferior.

## JLCPCB (PCBA estándar, SMT en la cara inferior + THT)

- BOM `jlcpcb/BOM_JLCPCB.csv` y CPL `jlcpcb/CPL_JLCPCB.csv` (SMD en «Bottom»; elegir «Assembly side: Bottom»).
- A mano (sin código LCSC, fuera del CPL): J20, F2 y los zócalos U1.
- En la vista previa de la cara inferior, revisar la orientación de Q1–Q3, D1–D3 (banda del cátodo hacia C2/+5 V, según la serigrafía inferior), R2/R4/R6 (verticales) y J6 (boca hacia la zona de 230 V); y la de las piezas THT giradas, J20 y F2 a 90°.

## Texto para pedir presupuesto a PCBWay

> Hello, please quote turnkey PCBA for the attached design (thermostat Rev C, 84 × 84 mm, 2 layers, 2 pcs).
> SMT on ONE side only, the BOTTOM side (all SMD parts incl. J6, FPC connector JUSHUO AFC07-S50ECA-00); through-hole parts on the top side.
> Before production, could your engineers please double-check two footprints against the datasheets:
> (1) Hongfa HF115F/005-1ZS3 relay (5 mm pinning, 16 A): COM must be the middle contact column, NC next to the coil and NO at the far end;
> (2) the AFC07-S50ECA-00 land pattern and its orientation (upper contact, opening towards the top edge of the board).
> The board carries 230 VAC: please keep the solder mask and silkscreen as designed in the area above the dashed line.
> Thank you!

## Al recibir las placas

1. Con el polímetro: ninguna continuidad entre COMP/VENT/CALOR/L y cualquier pin SELV (J1, J3, J5, J6, U1).
2. Relé: COM–NC cerrado en reposo; COM–NO cerrado con 5 V en la bobina.
3. Cortar a ras (≤ 1,5 mm) las patillas de la cara delantera en la zona de 230 V y colocar la lámina aislante antes de la pantalla.
4. Banco solo a 5 V: relés, arranque con la pantalla enchufada, SHT40 y consumo.
