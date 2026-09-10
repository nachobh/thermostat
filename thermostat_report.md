# Informe Detallado: Conexión de SSR y Uso de Capacitores para Termostato con ESP8266 NodeMCU

## 1. Conexión de SSR con ESP8266 NodeMCU

### a. Modelos de SSR disponibles
- **SSR-41FDA**: 8A 250VAC / 3-32VDC
- **S202S01**: 16A 250VAC

### b. Corriente de entrada de SSR
Los SSR típicamente tienen una entrada de tipo LED con una resistencia en serie. La corriente de entrada típica para SSR como estos es de 10-15mA a 5VDC. A 3.3VDC, la corriente será menor, pero probablemente suficiente para activar el SSR si el diseño interno lo permite.

### c. Corriente de salida de GPIO ESP8266
El ESP8266 puede suministrar hasta 12mA por pin GPIO, con un total recomendado de ~60mA para todos los pines. Esto significa que puede manejar directamente la entrada de los SSR si la corriente requerida es menor a 12mA.

### d. Conexión directa (recomendada)
Para conectar directamente el SSR al ESP8266:
1. Conecta el pin GPIO del ESP8266 al terminal positivo (+) del SSR a través de una resistencia limitadora de corriente (por ejemplo, 220Ω).
2. Conecta el terminal negativo (-) del SSR al GND del ESP8266.
3. Asegúrate de que la corriente de entrada del SSR no exceda los 12mA.

Ejemplo de conexión:
```
ESP8266 GPIO ----[220Ω]----> SSR Input (+)
                           SSR Input (-) ---- GND
```

### e. Conexión con transistor (opcional pero segura)
Si hay dudas sobre la corriente requerida o se desea mayor margen de seguridad:
1. Usa un transistor NPN (por ejemplo, 2N2222 o BC547).
2. Conecta el GPIO al transistor con una resistencia de base (1kΩ).
3. Conecta el colector del transistor al positivo del SSR y el emisor al GND.
4. Asegura una resistencia de pull-down (10kΩ) entre base y GND.

## 2. Uso de Capacitores en el Diseño

### a. Propósito de los capacitores
- **Decoupling/Bypass**: Reducir ruido en las líneas de alimentación y proporcionar corriente instantánea a los ICs.
- **Filtrado**: Suavizar picos de voltaje y transitorios.
- **Estabilidad**: Prevenir caídas de voltaje durante picos de corriente.

### b. Tipos y valores recomendados
- **Cerámicos (0.1µF)**: Colocar uno cerca de cada IC (ESP8266, DHT22, RTC, etc.) para filtrar ruido de alta frecuencia.
- **Electrolíticos (10µF-100µF)**: Colocar uno cerca del regulador de voltaje para estabilizar la alimentación general.
- **Cerámicos de 100nF**: Colocar uno cerca de la entrada de cada SSR para filtrar ruido de conmutación.

### c. Ubicación en la PCB
- Cerca de cada componente activo (ICs, sensores).
- Cerca del regulador de voltaje.
- Cerca de las entradas de SSR.
- En las líneas de alimentación principales (VCC/GND).

## 3. Consideraciones Adicionales

### a. Seguridad
- Mantén separación física entre circuitos de alta y baja tensión.
- Usa ranuras de aislamiento en la PCB si es de doble capa.
- Considera usar un fusible en la línea de 220VAC.

### b. Diseño en KiCad
1. Crea el esquemático con todos los componentes.
2. Asigna huellas (footprints) adecuadas.
3. Diseña la disposición de la PCB manteniendo las separaciones de seguridad.
4. Coloca los capacitores cerca de sus respectivos componentes.
5. Genera los archivos de fabricación (Gerber, taladro).

Este diseño permitirá controlar los SSR con el ESP8266 de manera segura y eficiente, manteniendo la estabilidad del circuito mediante el uso adecuado de capacitores.
