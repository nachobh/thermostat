# Termostato — Checklist de fabricación y entrega

Actualizado: 2026-09-10. Sustituye el checklist §9 del análisis (tenía un item
contradictorio: pedía "ninguna salida en GPIO15" cuando la decisión §5 mantiene el
SSR de calor en GPIO15 protegido por pull-down).

## 1. Firmware (`thermostat.ino`)

- [x] Pines sin cambios respecto al original (D7=frío, D8=calor, D6=ventilador,
      D5=DHT22, D3/D4 botones, D0 on/off, A0 pot)
- [x] NaN del DHT no mata el servidor web (`server.handleClient()` siempre)
- [x] Condición del ventilador simplificada (P8)
- [ ] Compilar con Arduino IDE / `arduino-cli` para ESP8266 y resolver warnings
- [ ] Clamp de rango en `/temp` (15–30 °C) — ver pending.md #10
- [ ] `Secrets.h` con credenciales fuera del repo + `Secrets.h.example` dentro
- [ ] Test en banco: sin carga AC, solo LEDs en lugar de SSR, verificar:
      - [ ] Arranque normal con GPIO15 "cargado" (simular LED SSR)
      - [ ] Lógica auto: Δt enciende frío/calor/ventilador según §1
      - [ ] Anti-ciclos: ningún cambio de estado más de 1 vez / 300 s
      - [ ] Endpoints: `/temp`, `/hot`, `/cold`, `/fan`, `/auto` responden
      - [ ] Interruptor OFF apaga todo y resetea los forced flags
      - [ ] DHT desconectado → web sigue viva, SSR no conmutan

## 2. Esquema (`sketch_pcb.fzz`)

- [x] 3× NPN con colector→SSR IN(+), emisor→GND (netlist verificado por script)
- [x] 3× 1k GPIO→base, 3× 10k base→GND (netlist verificado)
- [x] 100nF en paralelo con cada entrada SSR (netlist verificado)
- [x] Pull-ups 4.7k en SDA/SCL a 3V3 (netlist verificado)
- [x] Wires GPIO→SSR directos antiguos eliminados (netlist verificado)
- [x] DHT22 DATA→D5, VDD→3V3, GND→GND + 100nF (netlist verificado)
- [ ] Cambiar la parte RTC de DS1307 a DS3231 en el .fzz (pending #2)
- [ ] Añadir fusible + MOV + bornas AC al esquema, o documentar cableado externo (pending #3)
- [ ] Abrir en Fritzing y ordenar posiciones visuales de las partes nuevas (pending #4)
- [ ] Comprobar que Fritzing no reporta wires sueltos ni partes faltantes
- [ ] (Opcional) Cambiar parte OLED `grove_oled_128x96` por una 128×64 para que
      el esquema no confunda

## 3. Layout PCB (PCBWay 2 capas, 1.6 mm, HASL)

- [ ] Creepage AC/DC ≥ 6 mm entre zona 220 V y lógica 3.3 V
- [ ] SSR en la frontera: LED de entrada lado DC, triac lado AC
- [ ] Fusible en línea L antes de todo lo AC; MOV entre L y N junto a borna
- [ ] Ninguna traza DC bajo la zona AC; capa inferior = GND en zona AC
- [ ] Trazas entrada SSR ≥ 0.8 mm; alimentación ESP ≥ 1 mm
- [ ] Estrella de GND: potencia y lógico unidos en un punto cerca del NodeMCU
- [ ] DHT22 lejos de SSR y zona AC (deriva térmica)
- [ ] RTC en conector (no soldado) para cambio de pila
- [ ] DRC pasado con las separaciones AC antes de enviar
- [ ] Silk: identificar cada borna (L, N, FRÍO, CALOR, VENTILADOR) y cada SSR

## 4. Compra (BOM §4 del análisis)

- [ ] Medir amperaje real de cada carga ANTES de pedir → SSR-25DA elegido (pending #1 resuelto); confirmar pico de arranque con pinza al montar
- [ ] RTC: comprar DS3231 (no DS1307) + pila CR1220
- [ ] Verificar CTR/margen del SSR elegido a 3.3 V con el driver NPN (pending P7) — si no dispara firme, R base 1k→470Ω
- [ ] Interruptor: verificar que cierra contra GND (pending #14)
- [ ] Portafusibles + fusible 250 V 3–5 A + MOV 14D471K + bornas AC

## 5. Montaje y puesta en marcha

- [ ] Primer arranque SIN carga AC (todo fuera del SSR)
- [ ] Medir con multímetro: GPIO15 LOW al arrancar con el driver soldado
- [ ] Verificar cada canal por separado (frío → calor → ventilador) con pinza amperimétrica
- [ ] Comprobar temperatura de los SSR tras 30 min de operación continua
- [ ] Prueba de fallo: desconectar DHT22 en marcha → no debe conmutar nada, web viva
- [ ] Prueba de corte de luz → RTC mantiene hora, arranca en estado seguro (todo OFF)

## 6. Entrega / repo

- [ ] Commit de `thermostat.ino` corregido (lleva modificado desde `e326b9c`)
- [ ] Trackear `ANALISIS_PCB_THERMOSTAT.md`, `sketch_pcb.fzz`, `pending.md`, `checklist.md`
- [ ] Decidir destino de las fotos de WhatsApp (repo vs fuera)
- [ ] `thermostat_report.md` commiteado como referencia histórica
- [ ] README actualizado con: mapa de pines correcto, topología driver NPN,
      advertencia GPIO15, endpoints web, política del interruptor OFF
- [ ] Repo privado o credenciales rotadas si fue público (pending #5)
