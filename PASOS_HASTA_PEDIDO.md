# Termostato — pasos hasta el pedido

Actualizado: 2026-10-01.

## Estado real

**No pagar todavía sin la comprobación física 1:1.** El diseño vigente es
`thermostat_universal.fzz`, no `sketch_pcb.fzz` (archivo histórico). Es una
PCB de 100 × 100 mm, dos capas, exclusivamente SELV, con todos los módulos
externos. Está ruteada, exporta Gerber/Excellon y pasa el validador geométrico
independiente: 25 redes, 41 componentes, 103 pads, 1022 segmentos, 18 vías,
0 infracciones con 0,20 mm de separación mínima exigida. La menor separación
medida pista-pista es 0,237 mm. El paquete está en
`pcbway/thermostat_universal_rev_a/`.
Tiene cuatro taladros de fijación **NPTH Ø3,0 mm** en (5,5), (95,5), (5,95)
y (95,95) mm desde la esquina superior izquierda; separación entre centros
90 × 90 mm. Se reserva un radio de 3,5 mm sin componentes ni cobre.

Quedan pruebas físicas que ningún fichero puede sustituir: presentar las piezas
reales sobre una impresión 1:1, comprobar patillajes/polaridades, hacer una
revisión independiente y ensayar en banco a 5 V. La vista esquemática automática
de Fritzing es eléctricamente conexa pero visualmente densa; el pinout canónico
para revisar el cableado está en `PINOUT_Y_MONTAJE.md`.

## 1. Cableado que muestran las fotos

La etiqueta del Eberle Type 17225 7007 dice:

| Borne | Función impresa | En la foto |
|---:|---|---|
| 0 | SWITCH OUTPUT (4K/h) | sin cable |
| 1 | LOAD–HEATING | **con cable** |
| 2 | LOAD–COOLING | sin cable |
| 3 | LOAD–FAN | **con cable** |
| 4 | LOAD–COMPRESSOR | **con cable** |
| 5 | L1 (HOT) SUPPLY | **con cable** |
| 6 | N SUPPLY, AC 24 V | sin cable |
| 7 | N SUPPLY, AC 240 V | **con cable** |

Por tanto se necesitan exactamente tres salidas: calefacción (1), ventilador
(3) y compresor (4). Los bornes 0, 2 y 6 no se usan en esta instalación.

Cableado externo previsto, siempre sin tensión:

```text
borne 5 L ── protección ──┬── SSR HEATING ─── borne/cable 1
                          ├── SSR FAN ──────── borne/cable 3
                          └── SSR COMPRESSOR ─ borne/cable 4

borne 7 N ── se conserva aislado; sólo se usa como N de la protección L-N
              si ésta se instala. No entra en la PCB de control.
```

No inferir colores de conductor: etiquetar cada cable por su número antes de
soltarlo. Verificar continuidad con el equipo desconectado.

## 2. Arquitectura que evita repetir la PCB

La PCB contiene conectores para el NodeMCU, sensores y pantallas externos,
además de tres drivers NPN y sus componentes pasivos.
Cada canal termina en una borna de dos polos:

```text
USB/Vin 5 V ─────────────── Jx pin 0 (+5V) ── SSR+
GPIO ── 1 kΩ ── base BC547B
                 ├── 10 kΩ ── GND
GND ───────── emisor
              colector ──── Jx pin 1 (CTRL−) ── SSR−
```

Canales: D7/GPIO13 compresor, D8/GPIO15 calefacción y D6/GPIO12 ventilador.
El transistor a masa y el pull-down de 10 kΩ mantienen GPIO15 bajo durante el
arranque. El programa escribe LOW antes de declarar esos pines como salida.

Los SSR, el fusible, la protección contra sobretensión y todo el cobre de 240 V
van en una caja/compartimento externo. Así se puede cambiar un SSR sin volver a
pedir la placa y no existe separación AC/DC que dependa del layout de PCBWay.

## 3. Cálculos eléctricos y de separación

- 240 V RMS son `240 × √2 = 339,4 V` de pico normal, sin contar transitorios.
- 6 A a 240 V equivalen a un máximo aparente de `1,44 kVA`.
- Con una caída del SSR de 1,5 V, cada canal activo puede disipar
  `1,5 × 6 = 9 W`: disipador y pasta térmica son obligatorios.
- Tres entradas SSR de hasta 25 mA consumen como máximo 75 mA. Incluso sumando
  NodeMCU, WiFi, OLED, RTC y DHT, un cargador USB de 5 V/1 A deja margen. Al
  montar, medir 4,5–5,1 V entre `+5V` y GND con los tres SSR activados.

Si se pusiera red en la PCB —no es el diseño actual—, para 230/240 V, grado de
contaminación 2, FR-4 de grupo III desconocido y altitud ≤2.000 m:

| Supuesto | Impulso | Clearance básico | Clearance reforzado | Creepage básico/reforzado |
|---|---:|---:|---:|---:|
| Categoría II, equipo tras toma | 2,5 kV | 1,5 mm | 3,0 mm | 2,5 / 5,0 mm |
| Categoría III, instalación fija | 4,0 kV | 3,0 mm | 5,5 mm | 2,5 / 5,0 mm |

Para una instalación fija con USB accesible se adoptaría **8 mm** de keep-out
real en ambas caras y, si hiciera falta, ranura. No es un número arbitrario:
supera el caso reforzado CAT III de 5,5 mm y deja margen de fabricación. En el
diseño elegido la regla práctica es aún mejor: **ningún conductor de red en la
PCB**, y 8 mm mínimos entre metal vivo descubierto y la electrónica SELV dentro
de la caja, o una barrera aislante.

Que el cable de cobre antiguo haya funcionado a 6 A confirma corriente, no la
categoría de aislamiento ni el estado de su funda. Se reutiliza sin alargarlo,
si no presenta grietas o recalentamiento; las uniones serán con bornas de red,
punteras si el conductor es flexible y alivio de tracción.

## 4. SSR elegido y límites honestos

La interfaz de la placa queda fijada para SSR externo **DA**, entrada 3–32 VDC,
salida AC para 240 V y cruce por cero. La opción económica es:

- **3 × SSR-40DA genérico**, 3–32 VDC / 24–380 VAC, zero-cross, montaje de panel.
- Precio encontrado: 4,90 € IVA incluido por unidad; entrada anunciada 3–25 mA.
- Cada unidad con disipador, pasta térmica y cubierta sobre terminales.

Sobredimensionar la corriente nominal no perjudica el funcionamiento. Penaliza
tamaño, coste y disipador; tampoco convierte automáticamente un SSR resistivo de
“40 A” en uno de motor de 40 A. Un motor puede tomar 5–10 veces su corriente al
arrancar, por lo que hay que medir el pico y contrastarlo con la curva de surge.

La oferta económica anuncia 2,5 kVAC de aislamiento, pero no aporta una
certificación de aislamiento reforzado para instalación fija. La prueba térmica
no demuestra ese aislamiento. Si se exige conformidad verificable, el SSR barato
no basta: hay que comprar un modelo de fabricante con certificado y curva de
motor, aunque supere 5 €. Al quedar externo, cambiarlo no obliga a reimprimir.

No existe un porcentaje público y defendible de fallos de clones SSR-xxDA. Sin
fabricante, lote y ensayos con denominador, dar 1 %, 10 % o cualquier otra cifra
sería inventarlo. La unidad barata es compatible eléctricamente, pero no ofrece
la misma trazabilidad que un Crydom/Omron/Carlo Gavazzi. Para no arriesgar la
PCB, el SSR queda externo; para no arriesgar la instalación, cada unidad barata
debe superar la prueba del paso 8 antes de conectarse al equipo.

## 5. Protecciones externas

Sí se incorporan al diseño, pero en la caja de potencia, no en la PCB SELV:

1. Protección de sobrecorriente en L antes de dividir a los tres SSR. No fijar
   “5 A” o “10 A” a ciegas: debe ser ≤ capacidad del conductor y compatible con
   el pico de arranque. Si el circuito existente ya está protegido a 6 A,
   documentar su curva y poder de corte; si no, elegirla tras medir carga/pico.
2. **TMOV de 275 VAC**, por ejemplo Littelfuse TMOV14RP275E, entre L
   protegida y N. Se prefiere un varistor térmicamente protegido a un MOV desnudo.
3. Cubiertas de bornes, caja no propagadora, alivio de tracción y separación de
   8 mm/barrera respecto a SELV.
4. Un SSR suele fallar en cortocircuito. El fusible protege ante sobrecorriente,
   pero no garantiza apagar una carga normal si el triac queda pegado. Si se
   requiere apagado garantizado, añadir interruptor/seccionador o contactor
   mecánico aguas arriba; el interruptor lógico del NodeMCU no cumple esa función.

No se añade fuente AC/DC a la PCB: el cargador USB aislado de 5 V/1 A indicado
por el usuario es más barato y mantiene la red fuera del diseño.

## 6. Revisar el `.fzz` y preparar fabricación

Abrir `thermostat_universal.fzz` con Fritzing 1.0.1. El NodeMCU, OLED,
DS3231, DHT, potenciómetro y mandos quedan fuera de la PCB y se conectan con
mazos JST-XH polarizados de 2,50 mm; los tres SSR también son externos. No se
depende de la huella física del NodeMCU ni de los módulos.

- [x] Sustituir módulos por conectores JST-XH 3/4/5; bornas SSR Phoenix 5,08 mm.
- [x] Colocar 41 componentes en 100 × 100 mm y rutear las 25 redes SELV.
- [x] Comprobar continuidad y separaciones con `validate_universal_pcb.py`.
- [x] Exportar y abrir Gerber + Excellon; confirmar contorno y taladros.
- [ ] Imprimir a escala 1:1 y presentar los conectores, BC547B, PTC y pasivas
      reales antes de pagar.
- [ ] Segunda revisión independiente del pinout, orientación y Gerbers.
- [ ] Confirmar que uno de los OLED admite dirección 0x3D y el otro 0x3C; medir
      las pull-ups de los módulos y dejar las 4,7 kΩ de PCB sin poblar si sobran.
- [ ] Confirmar orientación C-B-E del BC547B real frente a su huella TO-92.

`build_universal_fzz.py` regenera el diseño vigente;
`validate_universal_pcb.py` comprueba el cobre. `repair_thermostat_fzz.py`
sólo conserva la reparación del diseño histórico `sketch_pcb.fzz`.

## 7. Firmware antes del banco

- [x] nombres de pines alineados con 1/3/4;
- [x] arranque seguro de GPIO15;
- [x] WiFi con timeout y operación local sin red;
- [x] RTC opcional;
- [x] media móvil del último minuto y descarte de lecturas a más de ±2 °C;
- [x] apagado inmediato si no queda ninguna lectura válida;
- [x] aliases `/heating` y `/compressor`, conservando `/hot` y `/cold`;
- [x] activaciones forzadas requieren `confirm=true`; apagar no;
- [x] apagado inmediato de cargas térmicas; el temporizador sólo impide el
      próximo arranque. El cambio forzado detiene primero la carga opuesta.
- [x] activación remota rechazada si no queda temperatura válida reciente;
- [x] `/temp` se valida a 15–30 °C y persiste hasta mover el potenciómetro;
- [x] credenciales fuera del código mediante `Secrets.h`.
- [x] D0/GPIO16 activo en HIGH, con pull-down físico de 10 kΩ y
      `INPUT_PULLDOWN_16`: interruptor abierto/cable suelto = OFF.
- [x] D3/GPIO0 y D4/GPIO2 con pull-ups físicos de 10 kΩ e internos; pulsadores a
      GND. Mantenerlos sin pulsar durante el arranque.

Compilado con Arduino CLI 1.5.1, core ESP8266 3.1.2, placa `nodemcuv2`, DHT
1.4.7, RTClib 2.1.4 y U8g2 2.36.19, sin credenciales WiFi: compilación OK.
Uso de IRAM: 61.471/65.536 bytes (93 %). Falta flashear y probar sobre el
NodeMCU real. Copiar `Secrets.h.example` a `Secrets.h` y usar las nuevas
credenciales locales; el termostato arranca offline si se deja vacío.

## 8. Verificaciones antes de pagar la PCB

- [x] Compilar el firmware para `nodemcuv2` con las librerías indicadas.
- [ ] Imprimir la plantilla al 100 % y presentar todas las piezas que se
      soldarán a la placa; comprobar taladros, paso, orientación, polaridad y
      espacio para conectar los mazos. Si algo no encaja, corregir y regenerar
      los Gerbers antes de pedir.
- [x] Incorporar cuatro agujeros NPTH Ø3,0 mm en las esquinas, con zona libre
      para cabeza/arandela y sin colisión de cobre.
- [ ] Confirmar que la caja admite 100 × 100 mm y cuatro centros a 90 × 90 mm,
      más la altura de las bornas y salida de cables. Ø3,0 mm es ajustado para
      tornillería M3: presentar el tornillo elegido antes de pagar; M2,5 tiene
      más holgura.
- [ ] Obtener una segunda revisión independiente del esquema, pinout y Gerbers.
- [x] Exportar Gerber + Excellon, abrirlos en `gerbv`, comprobar taladros, borde,
      texto, dimensiones y ausencia total de cobre de 240 V.
- [ ] Subir el ZIP al visor/DFM de PCBWay y comprobar las capas y dimensiones
      antes de pagar; este paso no puede cerrarse localmente.

Sólo después: PCBWay, 2 capas, FR-4 1,6 mm, 1 oz y HASL. Se puede pedir
**A, PCB desnuda** con la BOM manual, o **B, la misma PCB con montaje THT
turn-key de 38 referencias** según `BOM_PCBWAY_TURNKEY.csv` e
`INSTRUCCIONES_PCBA_TURNKEY.md`. En B, PCBWay debe confirmar disponibilidad,
dimensiones y cualquier sustitución antes de la aprobación final. R7–R9 siguen
sin montar en ambos casos.
El flasheo, las pruebas de banco y las de red **bloquean la puesta en servicio,
no el pedido de la PCB desnuda**: el firmware puede corregirse sin reimprimir.

## 9. Pruebas antes de instalar o energizar la red

- [ ] Flashear el firmware en el NodeMCU real.
- [ ] Banco sólo a 5 V, sustituyendo los SSR por LED/carga de prueba: verificar
      que los tres canales quedan OFF durante reset y boot.
- [ ] Confirmar que D8/GPIO15 mide LOW al arrancar.
- [ ] Probar DHT desconectado, RTC desconectado y WiFi inexistente.
- [ ] Abrir/cerrar cada endpoint, incluida la confirmación de activación.
- [ ] Montar cada SSR con disipador fuera de la PCB y probar primero con una
      carga resistiva protegida.
- [ ] A 6 A, mantener una hora y registrar temperatura de carcasa/disipador; no
      aceptar olor, decoloración, disparos erráticos ni temperatura creciente sin
      estabilizar.
- [ ] Medir corriente de marcha y pico de arranque de cada carga para cerrar SSR,
      fusible y disipador.
- [ ] Tras soldar la PCB, verificar continuidad, polaridad y ausencia de cortos;
      repetir las pruebas a 5 V con las piezas definitivas antes de conectarla
      a los SSR externos.

## Referencias técnicas

- [Catálogo Eberle, reguladores KLR](https://www.eberle-controls.com/fileadmin/Downloads/PDF/ebe_klimaregler_katalog.pdf)
- [Espressif: modo de arranque ESP8266 y GPIO15](https://docs.espressif.com/projects/esptool/en/latest/esp8266/advanced-topics/boot-mode-selection.html)
- [TI: cálculo IEC 60664 de creepage y clearance](https://www.ti.com/lit/ml/slup421/slup421.pdf)
- [Omron: selección, inrush y modos de fallo de SSR](https://www.ia.omron.com/product/cautions/18/safety_precautions.html)
- [Littelfuse: familia TMOV térmicamente protegida](https://www.littelfuse.com/assetdocs/varistors-tmov25s-datasheet?assetguid=19f0f08e-7381-4bcc-bdba-a5f6e51c63a7)
- [Oferta SSR-40DA usada para el precio y datos anunciados](https://www.hellasdigital.gr/electronics/relays/solid-state-relay-module-ssr-40da-40a-3-32vdc-24-380vac/)
