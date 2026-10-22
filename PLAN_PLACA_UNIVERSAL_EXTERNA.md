# Plan de placa universal con módulos externos

Actualizado: 2026-09-24. Implementado en `thermostat_universal.fzz` Rev A.

## Objetivo

Diseñar una única PCB de control de baja tensión que pueda fabricarse en PCBWay
y utilizarse inicialmente con todos los módulos disponibles conectados de forma
externa.

Este enfoque evita que una diferencia de dimensiones o patillaje en NodeMCU,
OLED, RTC, DHT o potenciómetro obligue a repetir la PCB.

La placa no contendrá ningún conductor ni componente conectado a 240 V.

## Contenido de la PCB

La placa incluirá solamente:

- tres drivers para las entradas de los SSR;
- BC547B y sus resistencias/condensadores, o equivalentes SMD;
- conectores de baja tensión para el NodeMCU y los periféricos;
- tres salidas `+5V/CTRL-` hacia los SSR externos;
- desacoplo y pull-ups I2C opcionales;
- serigrafía completa de señales y canales.

Los siguientes elementos permanecerán externos:

- NodeMCU ESP8266;
- dos OLED SSD1306;
- RTC DS3231;
- DHT11 o DHT22;
- potenciómetro;
- botones e interruptor de control;
- tres SSR;
- cargador USB aislado de 5 V/1 A;
- fusible, TMOV, disipadores y todo el cableado de 240 V.

## Conectores propuestos

| Conector | Señales |
|---|---|
| `NODE_POWER` | `5V`, `3V3`, `GND` |
| `NODE_OUTPUTS` | `D7_COMP`, `D8_HEAT`, `D6_FAN`, `GND` |
| `I2C` | `3V3`, `GND`, `D1_SCL`, `D2_SDA` |
| `DHT` | `3V3`, `GND`, `D5_DATA` |
| `POT` | `3V3`, `GND`, `A0` |
| `CONTROLS` | `D0`, `D3_MENU`, `D4_SELECT`, `GND`, `3V3` |
| `SSR_HEATING_1` | `+5V`, `CTRL-` |
| `SSR_FAN_3` | `+5V`, `CTRL-` |
| `SSR_COMPRESSOR_4` | `+5V`, `CTRL-` |

Los números 1, 3 y 4 corresponden a los bornes utilizados en la instalación
Eberle fotografiada: calefacción, ventilador y compresor respectivamente.

## Familias de conectores

Recomendación inicial:

- JST-XH para sensores, pantallas y controles de baja tensión;
- bornas de tornillo de paso 5,08 mm para las entradas de control de los SSR;
- un conector multipolar polarizado para el NodeMCU externo.

Los conectores Dupont de 2,54 mm pueden utilizarse en banco, pero no son la
opción preferida para una instalación permanente porque pueden aflojarse.

La Rev A usa JST-XH 3/4/5 vías y bornas Phoenix MKDS 2 vías. El pinout exacto
está en `PINOUT_Y_MONTAJE.md`; comprobar físicamente los mazos para evitar
invertir 5 V y GND.

## Driver de cada SSR

Cada canal utilizará esta topología:

```text
USB/Vin 5 V ───────────── salida +5V ── SSR+
GPIO ── 1 kΩ ── base BC547B
                 ├── 10 kΩ ── GND
GND ───────── emisor
              colector ── salida CTRL- ── SSR-
```

Asignación:

- D7/GPIO13: compresor, borne Eberle 4;
- D8/GPIO15: calefacción, borne Eberle 1;
- D6/GPIO12: ventilador, borne Eberle 3.

El pull-down de 10 kΩ y el latch LOW del firmware mantienen GPIO15 en el estado
requerido durante el arranque del ESP8266.

## Montaje Rev A y posible variante futura

### Variante A: montaje manual

- BC547B TO-92;
- resistencias y condensadores THT;
- conectores soldados manualmente;
- todos los módulos externos.

Esta variante permite reutilizar las piezas disponibles y reparar fácilmente la
placa.

### Variante B: ensamblaje THT PCBWay

- Utiliza el **mismo Gerber Rev A** y los mismos 38 componentes THT poblados.
- PCBWay puede suministrar y montar conectores, PTC, drivers y pasivas según
  `BOM_PCBWAY_TURNKEY.csv` y su confirmación de disponibilidad/alternativas.
- R7–R9 permanecen sin montar inicialmente; los módulos externos se conectan
  por los mismos mazos que en la variante A.

No hay huellas SMD en Rev A. Una segunda PCB rediseñada a SMD sólo tendría
sentido si la cotización THT resultara demasiado cara; requeriría nuevos
Gerbers y una validación de fabricación independiente.

## Diseño futuro completamente integrado

Una versión posterior podría sustituir el NodeMCU por:

- ESP-12F;
- regulador de 3,3 V;
- circuito de reset y arranque;
- interfaz de programación;
- protección y desacoplo propios.

Esa versión sería otra revisión de PCB. No es necesaria para validar el control
actual y aumentaría considerablemente el riesgo de la primera fabricación.

## Ventajas de empezar con todo externo

- no depende de las dimensiones exactas de los módulos;
- permite cambiar de proveedor o modelo sin repetir PCB;
- facilita medir y depurar cada señal;
- mantiene los 240 V completamente fuera de la placa;
- permite sustituir los SSR baratos por modelos industriales;
- la misma lógica puede probarse muchas veces reflasheando el NodeMCU;
- reduce el coste y el riesgo de la primera fabricación.

## Próximos pasos restantes

1. Imprimir la PCB a escala 1:1 y presentar los conectores y componentes reales.
2. Verificar cada mazo y polaridad; especialmente D0–3V3 y A0 del NodeMCU.
3. Realizar las pruebas de banco de `checklist.md`.
4. Segunda revisión independiente de Gerber y cableado; sólo entonces pagar.

## Relación con el diseño actual

`sketch_pcb.fzz` se conserva sólo como referencia histórica. La Rev A ruteada
es `thermostat_universal.fzz`; no enviar el archivo histórico a PCBWay.

La guía general de seguridad, cálculos y cableado de potencia continúa en
`PASOS_HASTA_PEDIDO.md`.
