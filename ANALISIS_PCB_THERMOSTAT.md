# Termostato ESP8266 — Análisis completo y plan para PCB (PCBWay)

Fecha: 2026-09-10 · Basado en: `thermostat.ino`, `sketch.fzz` (Fritzing 0.9.3b), `thermostat_report.md` (GPT 5.6), git `e326b9c`.

---

## 1. Qué es el proyecto

Termostato DIY para aire acondicionado (calor / frío / ventilador) con:

- **ESP8266 NodeMCU (LoLin)** — control, WiFi STA, web server `:80`, mDNS `esp8266`
- **2× OLED SSD1306 128×64** por I2C por software (u8g2): pantalla A (datos, 0x7A) y B (setpoint grande, 0x78)
- **RTC DS1307** en Fritzing (el código usa `RTC_DS3231` — ver problema P2)
- **DHT22** temperatura + humedad
- **Potenciómetro 100K** en A0 para el setpoint (mapeo 18 °C + lectura/128)
- **2 botones** (menú D3, seleccionar D4) e **interruptor on/off** en D0 (GPIO16)
- **3 SSR** (relés de estado sólido) para calor, frío y ventilador
- Lógica auto con histéresis por tiempo: ningún cambio de estado más de 1 vez cada 300 s (`isTimeForAChange`)
- Endpoints web: `/temp?temp=N`, `/hot?hot=true|false`, `/cold`, `/fan`, `/auto`

## 2. Mapa de conexiones REAL (extraído del XML de `sketch.fzz`)

| Señal | NodeMCU | Periféricos |
|---|---|---|
| GND común | GND | OLED A/B, RTC, POT, TOGGLE, SSR1/2/3 (pin −) |
| 3V3 | 3V3 | DHT22 VDD, OLED A/B, RTC, POT, TOGGLE |
| I2C SDA | D2 | OLED A, OLED B, RTC |
| I2C SCL | D1 | OLED A, OLED B, RTC |
| On/Off | D0 (GPIO16) | TOGGLE |
| Menú | D3 (GPIO0) | BTN_MENU |
| Seleccionar | D4 (GPIO2) | BTN_SEL |
| Setpoint | A0 | POT 100K |
| DHT22 DATA | D5 (GPIO14) | DHT22 |
| SSR frío (RED) | D7 (GPIO13) | SSR1 entrada |
| SSR calor (YELLOW) | D8 (GPIO15) | SSR2 entrada — boot: LOW firme garantizado por pull-down 10k en base del NPN |
| SSR ventilador (GREEN) | D6 (GPIO12) | SSR3 entrada |

Nota de colores: en el código `setColdOn()` enciende RED_PIN y `setHotOn()` enciende YELLOW_PIN — el rojo es FRÍO y el amarillo CALOR.

## 3. Problemas detectados

### P1 — Peligro de arranque en GPIO15 (CRÍTICO, no estaba en el informe GPT)
El ESP8266 exige **GPIO15 LOW al arrancar** (pin de modo de boot). El ventilador está en D8=GPIO15 con SSR conectado: la corriente por el LED de entrada del SSR puede mantener el pin "alto" y **bloquear el arranque** (watchdog / garbage en serie). Además GPIO12/13 (HSPI) también son problemáticos con niveles altos al boot si la carga los tira arriba.
**Solución:** mover los 3 SSR a pines seguros (ver §5) y, con el driver a transistor recomendado, añadir pull-down de 10 kΩ en cada base.

### P2 — Desajuste RTC: Fritzing DS1307 vs código `RTC_DS3231`
Registros compatibles pero comportamiento distinto de `lostPower()` y oscilador. **Solución recomendada: comprar el módulo DS3231** (mismo formato, más preciso, pines idénticos) y dejar el código como está. Actualizar la parte de Fritzing a DS3231.

### P3 — El `return` por NaN del DHT mata el servidor web
En `loop()`, si el DHT falla, el `return` (línea ~177) se ejecuta **antes** de `server.handleClient()`: sin sensor no hay control remoto. Corregido en el script (§6).

### P4 — Con el interruptor OFF no hay control remoto
La rama `controlOff` no atiende al servidor. Probablemente intencional (corte físico), pero conviene decidirlo: en la PCB el interruptor cortará SOLO la lógica (los SSR quedan alimentados). Mantener OFF = todo parado local y remoto es aceptable; documentado.

### P5 — Credenciales WiFi en claro en el .ino y en git
`STASSID`/`STAPSK` commiteados. Rotar contraseña si el repo fue público; usar `#define` externo o `Secrets.h` en el .gitignore.

### P6 — Fritzing sin resistencias ni capacitores
El propio informe GPT pide 220 Ω en serie con cada SSR y cerámicos 100 nF + electrolítico de bulk — **nada de eso está en el esquema**. Corregido en `sketch_pcb.fzz` (§7).

### P7 — SSR a 3.3 V sin margen
A 3.3 V la corriente de entrada del SSR es marginal según modelo (el informe lo admite). Con driver a transistor (§5) se resuelve el margen del GPIO y se protege el ESP; verificar el CTR con el SSR real comprado.

### P8 — Condición redundante del ventilador
`(t-temp >= 3 || t-temp <= -3 || ((t-temp >= 3 || t-temp <= -1) && h > 65))` — la primera cláusula contiene a parte de la tercera. Simplificable a `(t-temp >= 3 || t-temp <= -3 || (t-temp <= -1 && h > 65))`.

### P9 — Sin protección AC en el boceto
Falta fusible, varistor (MOV) y separación de creepage en la parte de 220 V. Obligatorio para una PCB segura (§8).

### P10 — I2C sin pull-ups explícitas
Los módulos OLED/RTC traen sus pull-ups internas, pero al llevar las líneas por PCB conviene 4.7 kΩ a 3.3 V explícitos en SDA/SCL.

## 4. BOM recomendado para PCBWay

| Ctd | Componente | Valor / nota |
|---|---|---|
| 1 | ESP8266 NodeMCU LoLin (o ESP-12F + regulador propio en revisión futura) | |
| 2 | OLED SSD1306 128×64 I2C | |
| 1 | RTC **DS3231** (no DS1307) + pila CR1220 | mismo footprint |
| 1 | DHT22 | |
| 1 | Potenciómetro 100K (trimmer 3362U o perilla) | |
| 2 | Botones pulsadores | |
| 1 | Interruptor SPST on/off | |
| 3 | SSR entrada DC 3–32 V (SSR-41FDA o S202S01 según carga) | S202S01 16A solo si la carga lo justifica |
| 3 | Transistor NPN TO-92 (BC547B / 2N2222A) | driver de SSR |
| 3 | Resistencia 1 kΩ ¼ W | base del transistor |
| 3 | Resistencia 10 kΩ ¼ W | pull-down base |
| 2 | Resistencia 4.7 kΩ | pull-ups I2C |
| 8 | Cerámico 100 nF | ESP8266, cada OLED, RTC, DHT22, entradas SSR |
| 1 | Electrolítico 100 µF / 16 V | bulk 3.3 V |
| 1 | Portafusibles + fusible 250 V 3–5 A | línea L AC |
| 1 | Varistor MOV 14D471K (o similar) | entre L y N |
| 1 | Bornas AC 2 posiciones + 3 salidas SSR | separación ≥ 6 mm |
| — | PCB 2 capas 5×7 cm (la del boceto) | |

## 5. Decisión final de pines: SE MANTIENEN los pines originales

Reevaluado: con **driver NPN + pull-down 10 kΩ en la base**, el GPIO15 (D8, SSR calor) queda con LOW firme al arranque, que es exactamente lo que exige el boot del ESP8266. No hace falta reasignar nada — mover pines solo añadiría riesgo de error sin beneficio. El script conserva D7=frío, D8=calor, D6=ventilador, D5=DHT22, D3/D4 botones, D0 on/off.

Topología por canal (×3, aplicada en `sketch_pcb.fzz`):

```
GPIO ──[1k]──┤B   C├── SSR IN(+) ──┬── [100nF] ──┬── SSR IN(−) ── GND
             │ NPN │               │              │
             └─E───┴──── GND ──────┘   [10k base-GND]
```

- 1 kΩ limita la corriente de base (~2.6 mA con 3.3 V, sobra para saturar un BC547 que conmuta los ~10 mA del LED del SSR con ganancia ≥100).
- 10 kΩ pull-down garantiza base en GND si el GPIO flota (boot, reset) → SSR apagado.
- 100 nF en paralelo con la entrada del SSR filtra transitorios de conmutación.

## 6. Correcciones aplicadas al script (`thermostat.ino`)

1. **NaN del DHT**: la comprobación se hace justo tras leer; si falla, se omite la lógica de control pero **`server.handleClient()` y `MDNS.update()` se ejecutan siempre** (el control remoto sobrevive a un sensor caído).
2. **Simplificación P8** de la condición del ventilador: `fanForcedOn || (!fanForcedOff && (Δ≥3 || Δ≤−3 || (Δ≤−1 && h>65)))`.
3. Comentarios en cabecera documentando la topología de driver y que los pines no cambian.

## 7. Correcciones aplicadas al Fritzing (`sketch_pcb.fzz`)

Nueva copia generada desde `sketch.fzz` (original intacto). Netlist verificado por script (union-find sobre el XML):

- **3× NPN (BC547/2N2222)**: colector → SSR IN(+) ; emisor → GND.
- **3× 1 kΩ** GPIO→base ; **3× 10 kΩ** base→GND.
- Los 3 wires GPIO→SSR directos antiguos (10098, 10112, 9828) **eliminados**.
- **100 nF en paralelo con cada entrada SSR** (IN+ ↔ IN−).
- **5× 100 nF** desacoplo: ESP8266, OLED A, OLED B, RTC, DHT22 (VCC↔GND).
- **1× 100 µF** electrolítico bulk en 3.3 V.
- **2× 4.7 kΩ** pull-ups en SDA (D2) y SCL (D1) a 3.3 V.

> ⚠️ Verificación manual obligatoria: abrir `sketch_pcb.fzz` en Fritzing y revisar la vista breadboard. La edición se hizo por XML programática: la conectividad (netlist) está verificada, pero la posición visual de las partes nuevas puede requerir arrastre para que el cableado se vea ordenado antes de exportar a PCB.

## 8. Reglas para el layout PCB (PCBWay, 2 capas)

1. **Separación AC/DC ≥ 6 mm** (creepage) entre la zona de 220 V (bornas, fusible, MOV, LOAD de los SSR) y toda la lógica de 3.3 V. Los SSR son el punto de cruce: colocarlos en la frontera, con el LED de entrada del lado DC y el triac del lado AC.
2. **Fusible en la línea L** antes de todo lo AC. MOV entre L y N junto a la borna.
3. **No rutear trazas DC bajo la zona AC.** Si la PCB es doble capa, usar la capa inferior solo para GND en la zona AC.
4. Trazas de entrada SSR: ≥ 0.8 mm (corriente LED pequeña, pero por robustez). Alimentación ESP8266: ≥ 1 mm (picos de WiFi ~300 mA).
5. Estrella de GND: GND de potencia (SSR/AC) y GND lógico se unen en un único punto cerca del regulador/NodeMCU.
6. El DHT22 lejos de los SSR y de la zona AC (térmico).
7. Conector para el RTC (no soldado fijo) para poder cambiar pila.
8. En el pedido a PCBWay: 2 capas, 1.6 mm, acabado HASL, y **revisar el DRC con las separaciones AC antes de fabricar**.

## 9. Checklist antes de enviar a PCBWay

> **Obsoleto**: sustituido por `checklist.md` (este §9 tenía un item contradictorio:
> "Ninguna salida de conmutación en GPIO15" choca con la decisión §5 de mantener
> el SSR de calor en GPIO15 protegido por pull-down 10k). Usar `checklist.md` y
> `pending.md` como referencias vivas.

## 10. Pendientes / decisiones abiertas

- ¿El interruptor OFF debe cortar también los SSR (seguridad total) o solo la lógica? (ahora: solo lógica)
- ¿S202S01 (16A) o SSR-41FDA (8A)? Depende de la carga real del AC — medir amperaje.
- Fotos de WhatsApp: no analizadas (el modelo actual no tiene torre de visión).
- Migra a ESP-12F suelto + regulador solo si se busca compactar en una segunda revisión.
