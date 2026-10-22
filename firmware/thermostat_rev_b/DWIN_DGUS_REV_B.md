# Pantalla DWIN (DGUS II, T5L) – mapa de variables para la Rev B

El firmware (`thermostat_rev_b.ino`) habla con la pantalla por UART a **115 200 baudios
8N1** (`DWIN_BAUD`; si se cambia en `T5L_CFG.CFG`, compilar con `-DDWIN_BAUD=…`).
Conexión J2: 1 = +5 V, 2 = GND, 3 = TX de la pantalla, 4 = RX de la pantalla.
**Solo variantes con UART TTL de 3,3 V**: una salida RS232 (± 12 V) destruiría GPIO0/GPIO2.

**Rev C con DMG48480F040_01WTCZ01:** la pantalla se enchufa por su FPC de 50 pines a J6
(pines 1–2 +5 V, 3–5 GND, 49 TX2, 50 RX2) y va montada **girada 180°** (el FPC sale por arriba).
En el proyecto DGUS hay que configurar la rotación de 180° en `T5L_CFG.CFG`, para la imagen y el
táctil. El proyecto se carga con el adaptador HDL662S del set (USB o microSD) **antes** de montar la
pantalla en la placa.

## Variables que escribe el ESP8266 (comando 0x82, cada 500 ms)

| VP | Contenido | Formato | Control DGUS sugerido |
|---|---|---|---|
| 0x1000 | temperatura ambiente | int16, décimas de °C (−9999 = sin sensor) | Data Variable, 1 decimal |
| 0x1001 | humedad | int16, décimas de % | Data Variable, 1 decimal |
| 0x1002 | consigna | int16, décimas de °C | Data Variable, 1 decimal |
| 0x1003 | estado | bits: 0 COMP · 1 CALOR · 2 VENT · 3 esperando antiarranque · 4 fallo de sensor · 5 OFF por J4 · 6 WiFi | Bit Icon (un icono por bit) |
| 0x1004 | modo | 0 auto · 1 calor forzado · 2 frío forzado · 3 solo ventilación · 4 OFF | Variable Icon |
| 0x1005 | hora (RTC) | 0–23 | Data Variable |
| 0x1006 | minuto (RTC) | 0–59 | Data Variable |
| 0x1007 | antiarranque pendiente | segundos | Data Variable |

## Teclas (Basic Touch → «Return Key Code»)

Configurar cada botón con VP **0x2000** y la subida automática activada; la pantalla
envía `5A A5 06 83 20 00 01 00 KK`.

| Código | Acción |
|---|---|
| 0x0001 | consigna + 0,5 °C |
| 0x0002 | consigna − 0,5 °C |
| 0x0010 | modo automático (borra los forzados) |
| 0x0011 | calefacción forzada |
| 0x0012 | frío forzado |
| 0x0013 | solo ventilación |
| 0x0014 | ventilador en automático |
| 0x0020 | encender/apagar (alternar) — Rev C |
| 0x0021 | encender — Rev C |
| 0x0022 | apagar — Rev C |

Apagado (tecla OFF en la Rev C o interruptor J4 en la Rev B): la pantalla solo muestra datos y se ignoran todas las teclas salvo las de encendido.
El antiarranque de 5 minutos sigue mandando: un «frío forzado» espera si hace falta
(bit 3 del estado y cuenta atrás en 0x1007).
