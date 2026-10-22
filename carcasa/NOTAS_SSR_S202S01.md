# SSR Sharp S202S01 – datos de la hoja (D4-A02301EN, 2004) y consecuencias

Fuente: `Descargas/sharp-microelectronics-s102s01.pdf` y `S102S01.PDF`. Etiqueta Eberle 17225 7007: AC 240 V 6 (3,5) A, AC 24 V 1 (1) A (24 V sin usar).

| Dato | Hoja | Consecuencia |
|---|---|---|
| Corriente de salida | 8 A rms máx. con Tc ≤ 80 °C y disipador; uso recomendado ≤ 80 % de la curva Fig. 2 | No son 16 A |
| Tensión de carga recomendada (S202S01) | 80–240 V rms; VDRM 600 V | 230 V +10 % = 253 V supera el rango recomendado, no el máximo |
| Carga mínima | 0,1 mA | Sin problema con ventilador/compresor/calefactor |
| Entrada | LED, VF 1,2 V típ. (1,4 máx.), **IF(ON) recomendada 16–24 mA**, IF(OFF) ≤ 0,1 mA, 50 mA máx. | Resistencia serie en el cable +5 V de J11–J13: **180 Ω 0,25 W** (17,5–23,3 mA en el peor caso con 5 V ±5 %) |
| Cruce por cero | No (S202S01). Existe el S202S02 con la misma huella | Valorar S202S02 para cargas inductivas |
| Snubber | Cs = 0,022 µF + Rs = 47 Ω entre los terminales de salida, y varistor cerca del triac | Añadir por canal; valores de partida, probar con la carga real |
| Pines | 1 = salida T2, 2 = salida T1, 3 = entrada +, 4 = entrada −; pasos 5,08 / 7,62 / 2,54 mm; longitud ≥ 11,2 mm | Entrada y salida del mismo lado: separar y aislar los cables |
| Cuerpo | 18,5 × 24,6 × 4,2 mm máx., taladro Ø3,2 M3, par 0,3–0,5 N·m | Coincide con 18 × 24 × 4 |
| Metal del cuerpo | Común al pin 1 (no conectar externamente) | Lámina aislante entre SSR y disipador si éste debe estar aislado; tratarlo como pieza bajo tensión |
| Rth(j-c) / Rth(j-a) | 4,5 / 40 °C/W | — |
| Disipación (Fig. 6) | ≈ 2 W a 2 A, 4,5 W a 4 A, 7,2 W a 6 A, 10 W a 8 A | A 6 A, ~7 W por SSR |
| Corriente vs. Ta (Fig. 2), lectura aproximada a 45 °C | sin disipador ≈ 1,9 A; placa Al 50×50×2 ≈ 4 A; 100×100×2 ≈ 6,4 A; 200×200×2 ≈ 8 A | Aplicar además el 80 % |

La placa de características del Eberle (6 A resistivos / 3,5 A inductivos) es el máximo del aparato completo, no por canal.

---

# Decisión 2026-10-21: relés electromecánicos (caja v4)

Los S202S01 quedan descartados para el calefactor (placa Eberle: 6 (3,5) A; el S202S01 da ~3 A por canal con este disipador y 8 A solo con disipadores enormes).

**Relé elegido:** Hongfa HF115F/005-1ZS3 (SPDT, 16 A 250 VAC, bobina 5 V, 62 Ω ≈ 80 mA, 29 × 12,7 × 15,7 mm; LCSC C9225). Alternativa: Omron G5LE-1E-DC5 (16 A, 62,5 Ω). Datos de listados de distribuidores; **falta contrastar con la hoja oficial de Hongfa** (potencia de bobina, material de contactos, huella exacta).

No se ha encontrado un relé de 16 A con bobina de 5 V ≤ 50 mA. El G5Q-1A4 DC5 (≈ 40 mA, 125 Ω) se descartó: su valor a 250 VAC aparece como 3–5 A según la fuente.

Consecuencias eléctricas:
- Diodo de rueda libre (1N4007 o 1N4148) soldado en los terminales de cada bobina, cátodo al lado +5 V (J11/J12/J13 pin 1). Sin resistencia en serie.
- BC547B a ≈ 80 mA: dentro de su máximo de 100 mA pero con poco margen.
- F1 (RXEF030, 0,30 A a 23 °C, menos con calor): no encender más de 2 bobinas a la vez (≈ 160 mA). Calor y frío deben quedar bloqueados en firmware; antiarranque del compresor 3–5 min.
- Mini-placa de potencia aparte (100 × 28 mm) con ≥ 8 mm hasta la zona SELV; bornas L + COMP + CALOR + VENT.
