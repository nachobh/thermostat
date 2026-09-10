# Termostato — Pendientes y decisiones abiertas

Actualizado: 2026-09-10. Compañero de `ANALISIS_PCB_THERMOSTAT.md` y `checklist.md`.

## A. Bloqueantes antes de fabricar la PCB

1. **Decidir SSR según carga real del AC.** RESUELTO 2026-09-10: carga declarada
   6 A inductivo / 3,5 A resistivo → **3× SSR-25DA zero-cross + disipador
   ~1–2 °C/W obligatorio** (~8,4 W disipados por SSR a 6 A). Ver
   `PIEZAS_Y_PEDIDO_PCBWAY.md` §1. Queda pendiente medir el pico de arranque
   real con pinza al montar (checklist §5).
2. **Actualizar la parte RTC del `sketch_pcb.fzz` de DS1307 a DS3231.** El código usa
   `RTC_DS3231`; el .fzz todavía instancia `Real_Time_Clock_Module___DS1307` (problema P2).
   Mismo footprint, pero la parte de Fritzing debe coincidir con lo que se compre.
3. **Fusible + MOV + bornas AC no están en el .fzz.** El BOM (§4) los pide pero la
   corrección §7 no los añadió. Hay que añadirlos al esquema antes del layout, o
   documentar explícitamente que la parte AC se cablea fuera de la PCB (borneta
   externa). No dejarlo ambiguo.
4. **Verificación manual en Fritzing.** La edición del .fzz fue programática: el netlist
   está verificado por script, pero las posiciones visuales de las partes nuevas
   (NPN, R, C) pueden requerir arrastre antes de exportar a PCB.

## B. Seguridad (no bloqueante pero importante)

5. **Credenciales WiFi fuera del repo (P5).** `STASSID`/`STAPSK` están en claro en
   `thermostat.ino` y el .ino está trackeado en git. Crear `Secrets.h` en
   `.gitignore` + `Secrets.h.example`, y ROTAR la contraseña del router si el repo
   llegó a ser público (revisar `git remote -v` y visibilidad).
6. **Boot GPIO15 depende 100% del hardware.** Con el pull-down 10k en la base del NPN
   el pin arranca LOW correcto. PERO: si alguien prueba el SSR conectado DIRECTO al
   GPIO (sin driver), el arranque puede bloquearse. Dejarlo así es aceptable porque
   la PCB siempre lleva el driver; documentar en el README para el futuro.
7. **Sin autenticación en el servidor web.** `/hot?hot=true` conmuta carga de 220 V
   desde cualquier dispositivo de la LAN. Para uso doméstico puede ser aceptable;
   mínimo no exponer el puerto 80 a internet (no port-forward, no UPnP).

## C. Decisiones de diseño abiertas

8. **Interruptor OFF: ¿corta solo lógica o también SSR?** Ahora (rama `controlOff`)
   corta todo local Y remoto, pero los SSR quedan alimentados en AC. Opciones:
   a) Mantener como está (corte total de comportamiento, SSR en standby).
   b) Que el interruptor corte la línea L de los SSR (seguridad total de mantenimiento).
   Implica cambios en el layout AC. Decidir antes de rutear.
9. **`lastChangeTime` común para los 3 canales.** DECIDIDO 2026-09-10: se MANTIENE
   el límite actual de 1 cambio / 300 s tal cual (verificado con visión que el
   termostato original Eberle admite 4.000 ciclos/h — vamos 300× por debajo).
   No hace falta independencia por canal.
10. **Rango del setpoint por web sin validar.** `/temp?temp=999` se acepta tal cual.
    Añadir clamp en `getTemp()` (p. ej. 15–30 °C). Cambio de 2 líneas.

## D. Limpieza de código (bajo riesgo, cuando se toque el .ino)

11. Los pines `MENU_PIN`/`SELECT_PIN` se leen por serial pero no tienen lógica de menú
    asociada — los botones están cableados en el .fzz pero el firmware no los usa.
    Decidir: implementar menú local o quitarlos del BOM/.fzz.
12. `u8g2` y `u8g2B` usan el MISMO par de pines SDA/SCL (soft I2C) con direcciones
    0x7A/0x78 — funciona, pero podría migrarse a `U8G2_SSD1306_128X64_NONAME_F_HW_I2C`
    para liberar CPU. Opcional.
13. `printT()` imprime `" %\t"` suelto en el log (sobra).
14. `CONTROL_PIN` (GPIO16) no es pin de interrupción profunda ni tiene pull-down
    interno — el `digitalWrite(CONTROL_PIN, HIGH)` activa la pull-up interna,
    correcto para el toggle actual, pero el interruptor debe cerrar a GND.
    Verificar que el interruptor comprado cierra contra GND, no contra 3V3.

## E. Repo / git

15. `thermostat.ino` modificado SIN commitear (último commit `e326b9c`).
16. Sin trackear: `ANALISIS_PCB_THERMOSTAT.md`, `sketch_pcb.fzz`, `pending.md`,
    `checklist.md`, fotos de WhatsApp. Decidir si las fotos van al repo (pesan
    ~2.7 MB en total) o se guardan aparte.
17. `thermostat_report.md` (informe GPT) sin trackear también — conviene
    commitearlo como referencia histórica junto al análisis.

## F. Verificado OK (no repetir)

- Netlist de `sketch_pcb.fzz` verificado por script: 3× canal NPN (GPIO→1k→base,
  colector→SSR+, emisor→GND, 10k base-GND, 100nF en entrada SSR), pull-ups I2C
  4.7k, desacoplos, DHT22→D5, TOGGLE→D0, botones→D3/D4, POT→A0. Coincide con el
  código y con §5 del análisis.
- Fix P3 (NaN DHT no mata el server) aplicado en el .ino.
- Fix P8 (condición ventilador simplificada) aplicado en el .ino.
- Tabla §2 del análisis corregida el 2026-09-10: ROJO=frío=D7, AMARILLO=calor=D8,
  VERDE=ventilador=D6 (coherente ya con §5 y con el código).
