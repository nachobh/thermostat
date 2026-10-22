// Termostato ESP8266 - PCB Rev B / Rev C (84 x 84 mm, reles en placa, pantalla DWIN 4").
// Ver REV_B.md, REV_C.md y DWIN_DGUS_REV_B.md. El mismo firmware sirve para las dos placas:
// los GPIO tienen la misma funcion (en la Rev C, RL2 es el ventilador y RL3 la calefaccion).
//
// Hardware Rev B:
//  - Tres reles Hongfa HF115F/005-1ZS3 en la PCB: +5V -> bobina A1, A2 -> colector
//    BC817-40, emisor -> GND, 1N4148W en antiparalelo con cada bobina. Base: 1k
//    desde el GPIO y 10k a GND (mantiene D8/GPIO15 bajo durante el boot).
//  - 5 V de un cargador externo aislado (>= 2 A) por J1 y F1 (PTC 1,1 A). Con la
//    pantalla y la NodeMCU sobra margen para tres bobinas, pero calefaccion y
//    compresor nunca coinciden, asi que el maximo real son dos.
//  - Borne J20: L, COMP (Eberle 4), CALOR (Eberle 1), VENT (Eberle 3); fusible F2 T6,3 A.
//  - Pantalla DWIN T5L 480x480 por UART TTL 3,3 V en J2: TX pantalla -> 1k -> D3/GPIO0,
//    RX pantalla <- 1k <- D4/GPIO2 (pull-ups de 10k: ambos pines deben estar altos al
//    arrancar). Sin potenciometro: la consigna se cambia en la pantalla o por /temp.
//  - Sensor: Sensirion SHT40 por I2C (0x44) en J3 de la Rev C, en una capsula fuera de la caja;
//    comparte el bus D1/D2 con el RTC DS3231 opcional (J5). Con -DUSE_DHT22=1 se usa el DHT22
//    en D5 (J3 de la Rev B).
//  - Encendido/apagado: en la Rev C desde la pantalla (teclas 0x0020-0x0022) o por /power, y se
//    recuerda tras un corte. Con -DUSE_ONOFF_SWITCH=1 manda el interruptor de J4 en D0 (Rev B).
//  - Actualizacion por WiFi (ArduinoOTA, nombre "termostato"): en la Rev C el USB de la NodeMCU
//    queda dentro de la caja. Contrasena opcional OTA_PASSWORD en Secrets.h.
#include <Arduino.h>
#include <ArduinoOTA.h>
#include <EEPROM.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <math.h>
#include <RTClib.h>
#include <SoftwareSerial.h>
#include <stdlib.h>
#include <WiFiClient.h>

#ifndef USE_DHT22
#define USE_DHT22 0
#endif
#if USE_DHT22
#include <DHT.h>
#ifndef DHTTYPE
#define DHTTYPE DHT22
#endif
#else
#include <Adafruit_SHT4x.h>
#endif
#ifdef __has_include
#if __has_include("Secrets.h")
#include "Secrets.h"
#endif
#endif
#ifndef STASSID
#define STASSID ""
#define STAPSK ""
#endif

const int DHTPin = 14;         // D5 (GPIO14) -> J3 DATA (solo Rev B con DHT22)
const int FAN_PIN = 12;        // D6 (GPIO12) -> RL3 -> J20 VENT (Eberle 3)
const int COMPRESSOR_PIN = 13; // D7 (GPIO13) -> RL1 -> J20 COMP (Eberle 4)
const int HEATING_PIN = 15;    // D8 (GPIO15) -> RL2 -> J20 CALOR (Eberle 1)
const int DWIN_RX_PIN = 0;     // D3 (GPIO0) <- TX de la pantalla (J2.3)
const int DWIN_TX_PIN = 2;     // D4 (GPIO2) -> RX de la pantalla (J2.4)
const int CONTROL_PIN = 16;    // D0 (GPIO16) <- J4 interruptor a 3V3 (solo Rev B)
#ifndef USE_ONOFF_SWITCH
#define USE_ONOFF_SWITCH 0
#endif
const char* ssid = STASSID;
const char* password = STAPSK;

// Antiarranque del compresor: espera minima entre cualquier cambio termico y el
// siguiente encendido (5 min; el apagado nunca se retrasa). Tambien cuenta desde
// el arranque, de modo que tras un corte de red el compresor espera 5 min.
constexpr unsigned long THERMAL_CHANGE_MS = 300000UL;
constexpr uint8_t MAX_ENERGISED_COILS = 2;  // calor y frio nunca juntos -> como mucho 2
constexpr unsigned long SENSOR_SAMPLE_MS = 2000UL;
constexpr unsigned long SENSOR_WINDOW_MS = 60000UL;
constexpr unsigned long WIFI_CONNECT_TIMEOUT_MS = 15000UL;
constexpr unsigned long DISPLAY_REFRESH_MS = 500UL;
constexpr unsigned long SETPOINT_SAVE_DELAY_MS = 10000UL;  // limita escrituras en flash
constexpr double SENSOR_OUTLIER_C = 2.0;
constexpr double CONTROL_HYSTERESIS_C = 0.5;
constexpr double DEFAULT_SETPOINT_C = 21.0;
constexpr double SETPOINT_MIN_C = 15.0;
constexpr double SETPOINT_MAX_C = 30.0;
constexpr double SETPOINT_STEP_C = 0.5;
constexpr size_t SENSOR_SAMPLE_COUNT = 30;

// Pantalla DWIN (DGUS II). Mapa de variables en DWIN_DGUS_REV_B.md.
#ifndef DWIN_BAUD
#define DWIN_BAUD 115200
#endif
constexpr uint16_t VP_ROOM_TEMP = 0x1000;   // int16, decimas de grado
constexpr uint16_t VP_HUMIDITY = 0x1001;    // int16, decimas de %
constexpr uint16_t VP_SETPOINT = 0x1002;    // int16, decimas de grado
constexpr uint16_t VP_STATUS = 0x1003;      // bits, ver STATUS_*
constexpr uint16_t VP_MODE = 0x1004;        // 0 auto, 1 calor, 2 frio, 3 solo vent., 4 OFF
constexpr uint16_t VP_HOUR = 0x1005;
constexpr uint16_t VP_MINUTE = 0x1006;
constexpr uint16_t VP_WAIT_S = 0x1007;      // segundos de antiarranque pendientes
constexpr uint16_t VP_KEY = 0x2000;         // codigo de tecla devuelto por la pantalla
constexpr uint16_t STATUS_COMP = 1 << 0;
constexpr uint16_t STATUS_HEAT = 1 << 1;
constexpr uint16_t STATUS_FAN = 1 << 2;
constexpr uint16_t STATUS_WAIT = 1 << 3;
constexpr uint16_t STATUS_SENSOR_FAULT = 1 << 4;
constexpr uint16_t STATUS_CONTROL_OFF = 1 << 5;
constexpr uint16_t STATUS_WIFI = 1 << 6;
enum DwinKey : uint16_t {
  KEY_SETPOINT_UP = 0x0001,
  KEY_SETPOINT_DOWN = 0x0002,
  KEY_MODE_AUTO = 0x0010,
  KEY_MODE_HEAT = 0x0011,
  KEY_MODE_COOL = 0x0012,
  KEY_MODE_FAN = 0x0013,
  KEY_FAN_AUTO = 0x0014,
  KEY_POWER_TOGGLE = 0x0020,
  KEY_POWER_ON = 0x0021,
  KEY_POWER_OFF = 0x0022,
};

boolean compressorOn;
boolean heatingOn;
boolean fanOn;

boolean fanForcedOn;
boolean fanForcedOff;
boolean heatingForcedOn;
boolean heatingForcedOff;
boolean compressorForcedOn;
boolean compressorForcedOff;

double temp = 0.00;
double t;
double h;
boolean controlOff = true;
boolean powerOn = true;            // encendido por software (Rev C); se guarda en flash
boolean sensorAvailable = false;
boolean rtcAvailable = false;
boolean mdnsAvailable = false;
unsigned long lastThermalChangeMs = 0;
unsigned long lastSensorReadMs = 0;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastDisplayMs = 0;
unsigned long setpointChangedMs = 0;
boolean setpointDirty = false;

struct SensorSample {
  double temperature;
  double humidity;
  unsigned long timestamp;
};

SensorSample sensorSamples[SENSOR_SAMPLE_COUNT];
size_t sensorSampleHead = 0;
size_t sensorSampleSize = 0;

DateTime rightNow;
String date;

ESP8266WebServer server(80);
#if USE_DHT22
DHT dht(DHTPin, DHTTYPE);
#else
Adafruit_SHT4x sht4;
boolean sht4Available = false;
#endif
RTC_DS3231 rtc;
SoftwareSerial dwin(DWIN_RX_PIN, DWIN_TX_PIN);

// Consigna persistente (EEPROM emulada en flash).
struct StoredSetpoint {
  uint32_t magic;
  int16_t tenths;
  uint8_t powerOn;
};
constexpr uint32_t SETPOINT_MAGIC = 0x54524332;  // "TRC2"

void setup() {
  // Fijar el latch antes de habilitar las salidas reduce pulsos durante el boot.
  digitalWrite(COMPRESSOR_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);
  digitalWrite(HEATING_PIN, LOW);
  pinMode(COMPRESSOR_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HEATING_PIN, OUTPUT);
#if USE_ONOFF_SWITCH
  // GPIO16/D0 has no normal pull-up. The switch closes D0 to 3V3 when ON;
  // the PCB's 10k pull-down (R15) makes a disconnected cable default to OFF.
  pinMode(CONTROL_PIN, INPUT_PULLDOWN_16);
#endif

  Serial.begin(115200);
  dwin.begin(DWIN_BAUD);

  loadSetpoint();
  startSensor();
  startRtc();

  WiFi.mode(WIFI_STA);
  unsigned long wifiStarted = millis();
  if (strlen(ssid) > 0) {
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED && millis() - wifiStarted < WIFI_CONNECT_TIMEOUT_MS) {
      delay(250);
      Serial.print(".");
    }
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi unavailable; local thermostat remains active");
  }

  mdnsAvailable = WiFi.status() == WL_CONNECTED && MDNS.begin("termostato");
  if (mdnsAvailable) {
    Serial.println("MDNS responder started");
  }

  server.on("/", handleRoot);
  server.onNotFound(handleNotFound);
  server.on("/temp", HTTP_GET, getTemp);
  server.on("/hot", HTTP_GET, forceHot);
  server.on("/cold", HTTP_GET, forceCold);
  server.on("/heating", HTTP_GET, forceHot);
  server.on("/compressor", HTTP_GET, forceCold);
  server.on("/fan", HTTP_GET, forceFan);
  server.on("/auto", HTTP_GET, setAuto);
  server.on("/power", HTTP_GET, setPower);

  server.begin();
  Serial.println("HTTP server started");
  startOta();

  // Conserva la espera de 300 s tras cada arranque antes de energizar una carga termica.
  lastThermalChangeMs = millis();
}

boolean readControlOff(void) {
#if USE_ONOFF_SWITCH
  return !digitalRead(CONTROL_PIN);
#else
  return !powerOn;
#endif
}

void loop() {
  controlOff = readControlOff();
  pollDisplay();

  if (controlOff) {
    clearForcedModes();
    allOutputsOffImmediate();
  } else {
    sensorAvailable = updateFilteredSensor();
    if (!sensorAvailable) {
      // Sin una medida valida del ultimo minuto, el unico fallback seguro es apagar.
      allOutputsOffImmediate();
    } else {
      if (compressorForcedOn || (!heatingForcedOn && !compressorForcedOff && t > temp + CONTROL_HYSTERESIS_C)) {
        setCompressorOn();
      } else if (heatingForcedOn || (!compressorForcedOn && !heatingForcedOff && t < temp - CONTROL_HYSTERESIS_C)) {
        setHeatingOn();
      } else if (!compressorForcedOn && !heatingForcedOn &&
                 t >= temp - CONTROL_HYSTERESIS_C && t <= temp + CONTROL_HYSTERESIS_C) {
        setThermalOff();
      }

      // Nunca dejar compresor o calefaccion activos sin ventilacion.
      if (fanForcedOn || (!fanForcedOff && (compressorOn || heatingOn ||
          t - temp >= 3 || t - temp <= -3 || (t - temp <= -1 && h > 65)))) {
        setFanOn();
      } else {
        setFanOff();
      }

      enforceCoilBudget();
    }
  }

  updateDate();
  saveSetpointIfStable();
  if (millis() - lastDisplayMs >= DISPLAY_REFRESH_MS) {
    lastDisplayMs = millis();
    refreshDisplay();
  }

  server.handleClient();
  ArduinoOTA.handle();
  if (mdnsAvailable) {
    MDNS.update();
  }
  maintainWifi();
  delay(10);
}

// ---------------------------------------------------------------------------
// Pantalla DWIN: tramas 5A A5 LEN CMD ...  (0x82 escribe VP, 0x83 lectura/subida)
// ---------------------------------------------------------------------------

void dwinWriteWord(uint16_t vp, int16_t value) {
  const uint8_t frame[] = {0x5A, 0xA5, 0x05, 0x82,
                           (uint8_t)(vp >> 8), (uint8_t)(vp & 0xFF),
                           (uint8_t)((uint16_t)value >> 8), (uint8_t)((uint16_t)value & 0xFF)};
  dwin.write(frame, sizeof(frame));
}

int16_t tenths(double value) {
  return (int16_t)lround(value * 10.0);
}

void refreshDisplay(void) {
  uint16_t status = 0;
  if (compressorOn) status |= STATUS_COMP;
  if (heatingOn) status |= STATUS_HEAT;
  if (fanOn) status |= STATUS_FAN;
  if (!thermalChangeAllowed()) status |= STATUS_WAIT;
  if (!sensorAvailable) status |= STATUS_SENSOR_FAULT;
  if (controlOff) status |= STATUS_CONTROL_OFF;
  if (WiFi.status() == WL_CONNECTED) status |= STATUS_WIFI;

  uint16_t mode = 0;
  if (controlOff) mode = 4;
  else if (heatingForcedOn) mode = 1;
  else if (compressorForcedOn) mode = 2;
  else if (fanForcedOn && heatingForcedOff && compressorForcedOff) mode = 3;

  unsigned long elapsed = millis() - lastThermalChangeMs;
  uint16_t waitSeconds = elapsed >= THERMAL_CHANGE_MS ? 0 : (THERMAL_CHANGE_MS - elapsed + 999UL) / 1000UL;

  dwinWriteWord(VP_ROOM_TEMP, sensorAvailable ? tenths(t) : (int16_t)-9999);
  dwinWriteWord(VP_HUMIDITY, sensorAvailable ? tenths(h) : (int16_t)-9999);
  dwinWriteWord(VP_SETPOINT, tenths(temp));
  dwinWriteWord(VP_STATUS, (int16_t)status);
  dwinWriteWord(VP_MODE, (int16_t)mode);
  dwinWriteWord(VP_WAIT_S, (int16_t)waitSeconds);
  if (rtcAvailable) {
    dwinWriteWord(VP_HOUR, rightNow.hour());
    dwinWriteWord(VP_MINUTE, rightNow.minute());
  }
}

// Recoge una trama completa y procesa las teclas (VP_KEY, subida automatica 0x83).
void pollDisplay(void) {
  static uint8_t frame[32];
  static uint8_t length = 0;
  static uint8_t expected = 0;
  while (dwin.available()) {
    uint8_t byteRead = (uint8_t)dwin.read();
    if (length == 0 && byteRead != 0x5A) continue;
    if (length == 1 && byteRead != 0xA5) {
      length = 0;
      continue;
    }
    frame[length++] = byteRead;
    if (length == 3) {
      expected = byteRead;
      if (expected < 3 || expected > sizeof(frame) - 3) {
        length = 0;
        continue;
      }
    }
    if (length >= 3 && length == expected + 3) {
      // frame: 5A A5 LEN 83 VPH VPL N D0H D0L ...
      if (frame[3] == 0x83 && expected >= 6) {
        uint16_t vp = ((uint16_t)frame[4] << 8) | frame[5];
        uint16_t value = ((uint16_t)frame[7] << 8) | frame[8];
        if (vp == VP_KEY) handleKey(value);
      }
      length = 0;
    }
  }
}

void setPowerOn(boolean on) {
  powerOn = on;
  if (!on) {
    clearForcedModes();
    allOutputsOffImmediate();
  }
  setpointDirty = true;            // se guarda junto con la consigna
  setpointChangedMs = millis();
}

void handleKey(uint16_t key) {
#if !USE_ONOFF_SWITCH
  if (key == KEY_POWER_TOGGLE || key == KEY_POWER_ON || key == KEY_POWER_OFF) {
    setPowerOn(key == KEY_POWER_ON || (key == KEY_POWER_TOGGLE && !powerOn));
    lastDisplayMs = 0;
    return;
  }
#endif
  // Apagado (interruptor de J4 en la Rev B o tecla OFF en la Rev C): la pantalla solo muestra.
  if (controlOff) return;
  switch (key) {
    case KEY_SETPOINT_UP:
      changeSetpoint(temp + SETPOINT_STEP_C);
      break;
    case KEY_SETPOINT_DOWN:
      changeSetpoint(temp - SETPOINT_STEP_C);
      break;
    case KEY_MODE_AUTO:
      clearForcedModes();
      break;
    case KEY_MODE_HEAT:
      if (!sensorAvailable) break;
      compressorForcedOn = false;
      compressorForcedOff = true;
      heatingForcedOn = true;
      heatingForcedOff = false;
      setCompressorOff();
      setHeatingOn();
      break;
    case KEY_MODE_COOL:
      if (!sensorAvailable) break;
      heatingForcedOn = false;
      heatingForcedOff = true;
      compressorForcedOn = true;
      compressorForcedOff = false;
      setHeatingOff();
      setCompressorOn();
      break;
    case KEY_MODE_FAN:
      // Solo ventilacion: termico apagado y ventilador forzado.
      heatingForcedOn = false;
      compressorForcedOn = false;
      heatingForcedOff = true;
      compressorForcedOff = true;
      fanForcedOn = true;
      fanForcedOff = false;
      setThermalOff();
      setFanOn();
      break;
    case KEY_FAN_AUTO:
      fanForcedOn = false;
      fanForcedOff = false;
      break;
    default:
      Serial.print("DWIN: tecla desconocida 0x");
      Serial.println(key, HEX);
      return;
  }
  lastDisplayMs = 0;  // refresco inmediato
}

void changeSetpoint(double requested) {
  temp = constrain(round(requested * 2.0) / 2.0, SETPOINT_MIN_C, SETPOINT_MAX_C);
  setpointDirty = true;
  setpointChangedMs = millis();
}

void loadSetpoint(void) {
  EEPROM.begin(sizeof(StoredSetpoint));
  StoredSetpoint stored;
  EEPROM.get(0, stored);
  double value = stored.tenths / 10.0;
  if (stored.magic == SETPOINT_MAGIC && value >= SETPOINT_MIN_C && value <= SETPOINT_MAX_C) {
    temp = value;
    powerOn = stored.powerOn != 0;
  } else {
    temp = DEFAULT_SETPOINT_C;
    powerOn = true;
  }
}

void saveSetpointIfStable(void) {
  if (!setpointDirty || millis() - setpointChangedMs < SETPOINT_SAVE_DELAY_MS) return;
  StoredSetpoint stored = {SETPOINT_MAGIC, tenths(temp), (uint8_t)(powerOn ? 1 : 0)};
  EEPROM.put(0, stored);
  EEPROM.commit();
  setpointDirty = false;
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------

void getTemp()
{
  if (!server.hasArg("temp")) {
    server.send(400, "text/plain", "Falta el parametro temp");
    return;
  }
  String requested = server.arg("temp");
  char *end = nullptr;
  double requestedTemperature = strtod(requested.c_str(), &end);
  if (end == requested.c_str() || *end != '\0' || !isfinite(requestedTemperature)) {
    server.send(400, "text/plain", "Temperatura no valida");
    return;
  }
  changeSetpoint(requestedTemperature);
  server.send(200, "text/plain", String("Temperatura cambiada a " + String(temp)));
}

void forceHot()
{
  if (!remoteControlAllowed()) return;
  boolean requestedOn = requestedTrue("hot", "heating");
  if (requestedOn && !activationConfirmed()) return;
  if (requestedOn && !activationSensorAvailable()) return;
  heatingForcedOn = requestedOn;
  heatingForcedOff = !heatingForcedOn;
  if (heatingForcedOn) {
    compressorForcedOn = false;
    compressorForcedOff = false;
    // Detener la carga opuesta inmediatamente; el nuevo arranque espera
    // el intervalo anticiclo a partir de ese apagado.
    setCompressorOff();
    setHeatingOn();
  } else {
    setHeatingOff();
  }
  server.send(200, "text/plain", String("Calefaccion solicitada: " + String(heatingForcedOn)));
}

void forceCold()
{
  if (!remoteControlAllowed()) return;
  boolean requestedOn = requestedTrue("cold", "compressor");
  if (requestedOn && !activationConfirmed()) return;
  if (requestedOn && !activationSensorAvailable()) return;
  compressorForcedOn = requestedOn;
  compressorForcedOff = !compressorForcedOn;
  if (compressorForcedOn) {
    heatingForcedOn = false;
    heatingForcedOff = false;
    setHeatingOff();
    setCompressorOn();
  } else {
    setCompressorOff();
  }
  server.send(200, "text/plain", String("Compresor solicitado: " + String(compressorForcedOn)));
}

void forceFan()
{
  if (!remoteControlAllowed()) return;
  boolean requestedOn = server.arg(String("fan")).equals("true");
  if (requestedOn && !activationConfirmed()) return;
  if (requestedOn && !activationSensorAvailable()) return;
  fanForcedOn = requestedOn;
  fanForcedOff = !fanForcedOn;
  if (fanForcedOn) {
    setFanOn();
  } else {
    setFanOff();
  }
  server.send(200, "text/plain", String("Ventilador establecido a " + String(fanForcedOn)));
}

void setAuto()
{
  boolean autoMode = server.arg(String("auto")).equals("true");
  if (autoMode) {
    clearForcedModes();
    server.send(200, "text/plain", String("Establecido modo auto"));
  } else {
    server.send(400, "text/plain", String("Usa auto=true"));
  }
}

void setPower()
{
#if USE_ONOFF_SWITCH
  server.send(409, "text/plain", "Esta placa usa el interruptor de J4");
#else
  if (!server.hasArg("on")) {
    server.send(400, "text/plain", "Usa on=true u on=false");
    return;
  }
  setPowerOn(server.arg("on").equals("true"));
  server.send(200, "text/plain", String("Termostato ") + (powerOn ? "encendido" : "apagado"));
#endif
}

void clearForcedModes(void) {
  fanForcedOn = false;
  fanForcedOff = false;
  heatingForcedOn = false;
  heatingForcedOff = false;
  compressorForcedOn = false;
  compressorForcedOff = false;
}

void startSensor(void) {
#if USE_DHT22
  dht.begin();
#else
  // Wire usa SDA = D2 (GPIO4) y SCL = D1 (GPIO5), el mismo bus que el RTC.
  sht4Available = sht4.begin();
  if (sht4Available) {
    sht4.setPrecision(SHT4X_HIGH_PRECISION);
    sht4.setHeater(SHT4X_NO_HEATER);
  } else {
    Serial.println(F("SHT40 not found on I2C (0x44)"));
  }
#endif
}

// Devuelve false si la lectura no es valida; deja NAN en ambos valores.
boolean readSensor(double &temperature, double &humidity) {
  temperature = NAN;
  humidity = NAN;
#if USE_DHT22
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
#else
  if (!sht4Available) {
    sht4Available = sht4.begin();   // reintento si el cable se conecto despues del arranque
    if (!sht4Available) return false;
    sht4.setPrecision(SHT4X_HIGH_PRECISION);
  }
  sensors_event_t humidityEvent, temperatureEvent;
  if (!sht4.getEvent(&humidityEvent, &temperatureEvent)) {
    sht4Available = false;
    return false;
  }
  temperature = temperatureEvent.temperature;
  humidity = humidityEvent.relative_humidity;
#endif
  return !isnan(temperature) && !isnan(humidity);
}

void startOta(void) {
  ArduinoOTA.setHostname("termostato");
#ifdef OTA_PASSWORD
  ArduinoOTA.setPassword(OTA_PASSWORD);
#endif
  // Durante una actualizacion, todas las cargas fuera.
  ArduinoOTA.onStart([]() { allOutputsOffImmediate(); });
  ArduinoOTA.begin();
}

void startRtc(void) {
  if (!rtc.begin()) {
    Serial.println(F("RTC unavailable; using millis() for control timing"));
    rtcAvailable = false;
    return;
  }

  rtcAvailable = true;
  if (rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
}

void maintainWifi(void) {
  if (strlen(ssid) == 0) return;
  if (WiFi.status() == WL_CONNECTED) {
    if (!mdnsAvailable) {
      mdnsAvailable = MDNS.begin("termostato");
    }
    return;
  }

  mdnsAvailable = false;
  if (millis() - lastWifiAttemptMs >= 30000UL) {
    lastWifiAttemptMs = millis();
    WiFi.disconnect();
    WiFi.begin(ssid, password);
  }
}

boolean remoteControlAllowed(void) {
  // Leer el interruptor también dentro del handler: una petición HTTP no debe
  // basarse únicamente en el estado cacheado al comienzo de loop().
  controlOff = readControlOff();
  if (!controlOff) return true;
  server.send(409, "text/plain", "Termostato apagado: orden rechazada");
  return false;
}

boolean activationSensorAvailable(void) {
  double averageTemperature = 0.0;
  double averageHumidity = 0.0;
  if (recentSensorAverage(averageTemperature, averageHumidity)) return true;
  server.send(409, "text/plain", "Sin temperatura valida reciente: activacion rechazada");
  return false;
}

boolean requestedTrue(const char* legacyArg, const char* descriptiveArg) {
  if (server.hasArg(descriptiveArg)) {
    return server.arg(descriptiveArg).equals("true");
  }
  return server.arg(legacyArg).equals("true");
}

boolean activationConfirmed(void) {
  if (server.hasArg("confirm") && server.arg("confirm").equals("true")) return true;
  server.send(409, "text/plain", "Confirma la activacion repitiendo con &confirm=true");
  return false;
}

// ---------------------------------------------------------------------------
// Sensor
// ---------------------------------------------------------------------------

boolean recentSensorAverage(double &averageTemperature, double &averageHumidity) {
  double temperatureSum = 0.0;
  double humiditySum = 0.0;
  size_t valid = 0;
  unsigned long now = millis();

  for (size_t i = 0; i < sensorSampleSize; ++i) {
    size_t index = (sensorSampleHead + SENSOR_SAMPLE_COUNT - sensorSampleSize + i) % SENSOR_SAMPLE_COUNT;
    if (now - sensorSamples[index].timestamp <= SENSOR_WINDOW_MS) {
      temperatureSum += sensorSamples[index].temperature;
      humiditySum += sensorSamples[index].humidity;
      ++valid;
    }
  }

  if (valid == 0) return false;
  averageTemperature = temperatureSum / valid;
  averageHumidity = humiditySum / valid;
  return true;
}

void addSensorSample(double temperature, double humidity) {
  sensorSamples[sensorSampleHead] = {temperature, humidity, millis()};
  sensorSampleHead = (sensorSampleHead + 1) % SENSOR_SAMPLE_COUNT;
  if (sensorSampleSize < SENSOR_SAMPLE_COUNT) ++sensorSampleSize;
}

boolean updateFilteredSensor(void) {
  double averageTemperature = 0.0;
  double averageHumidity = 0.0;
  boolean haveRecentAverage = recentSensorAverage(averageTemperature, averageHumidity);

  if (lastSensorReadMs != 0 && millis() - lastSensorReadMs < SENSOR_SAMPLE_MS) {
    if (haveRecentAverage) {
      t = averageTemperature;
      h = averageHumidity;
    }
    return haveRecentAverage;
  }

  lastSensorReadMs = millis();
  double measuredTemperature, measuredHumidity;

  if (!readSensor(measuredTemperature, measuredHumidity)) {
    Serial.println("Sensor read failed; using the last-minute average");
  } else if (haveRecentAverage && fabs(measuredTemperature - averageTemperature) > SENSOR_OUTLIER_C) {
    Serial.println("Sensor temperature outlier discarded");
  } else {
    addSensorSample(measuredTemperature, measuredHumidity);
    haveRecentAverage = recentSensorAverage(averageTemperature, averageHumidity);
    Serial.printf("Setpoint %.1f C  Temperature %.1f C  Humidity %.1f %%\r\n", temp, measuredTemperature,
                  measuredHumidity);
  }

  if (!haveRecentAverage) return false;
  t = averageTemperature;
  h = averageHumidity;
  return true;
}

// ---------------------------------------------------------------------------
// Salidas
// ---------------------------------------------------------------------------

uint8_t energisedCoils(void) {
  return (compressorOn ? 1 : 0) + (heatingOn ? 1 : 0) + (fanOn ? 1 : 0);
}

// Red de seguridad: calefaccion y compresor jamas a la vez, y nunca mas de
// MAX_ENERGISED_COILS bobinas activas. Si se incumple, todo a OFF.
void enforceCoilBudget(void) {
  if ((compressorOn && heatingOn) || energisedCoils() > MAX_ENERGISED_COILS) {
    allOutputsOffImmediate();
  }
}

boolean thermalChangeAllowed(void) {
  return millis() - lastThermalChangeMs >= THERMAL_CHANGE_MS;
}

void allOutputsOffImmediate(void) {
  boolean thermalWasOn = compressorOn || heatingOn;
  digitalWrite(COMPRESSOR_PIN, LOW);
  digitalWrite(HEATING_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);
  compressorOn = false;
  heatingOn = false;
  fanOn = false;
  if (thermalWasOn) lastThermalChangeMs = millis();
}

void setCompressorOn(void) {
  if (compressorOn || !thermalChangeAllowed()) return;
  digitalWrite(HEATING_PIN, LOW);
  digitalWrite(COMPRESSOR_PIN, HIGH);
  heatingOn = false;
  compressorOn = true;
  lastThermalChangeMs = millis();
}

void setCompressorOff(void) {
  if (!compressorOn) return;
  // La espera anticiclo sólo limita el próximo encendido, nunca el apagado.
  digitalWrite(COMPRESSOR_PIN, LOW);
  compressorOn = false;
  lastThermalChangeMs = millis();
}

void setHeatingOn(void) {
  if (heatingOn || !thermalChangeAllowed()) return;
  digitalWrite(COMPRESSOR_PIN, LOW);
  digitalWrite(HEATING_PIN, HIGH);
  compressorOn = false;
  heatingOn = true;
  lastThermalChangeMs = millis();
}

void setHeatingOff(void) {
  if (!heatingOn) return;
  // Una orden de apagado debe poder detener la carga inmediatamente.
  digitalWrite(HEATING_PIN, LOW);
  heatingOn = false;
  lastThermalChangeMs = millis();
}

void setThermalOff(void) {
  if (!compressorOn && !heatingOn) return;
  digitalWrite(COMPRESSOR_PIN, LOW);
  digitalWrite(HEATING_PIN, LOW);
  compressorOn = false;
  heatingOn = false;
  lastThermalChangeMs = millis();
}

void setFanOn(void) {
  digitalWrite(FAN_PIN, HIGH);
  fanOn = true;
}

void setFanOff(void) {
  // Una orden forzada de apagado no vence la ventilacion requerida por una carga termica.
  if (compressorOn || heatingOn) {
    setFanOn();
    return;
  }
  digitalWrite(FAN_PIN, LOW);
  fanOn = false;
}

// ---------------------------------------------------------------------------
// Fecha y web
// ---------------------------------------------------------------------------

void updateDate(void) {
  if (!rtcAvailable) {
    date = "UP ";
    date += String(millis() / 1000UL);
    date += "s";
    return;
  }
  rightNow = rtc.now();
  char buffer[32];
  snprintf(buffer, sizeof(buffer), "%04d-%02d-%02d %02d:%02d:%02d", rightNow.year(), rightNow.month(),
           rightNow.day(), rightNow.hour(), rightNow.minute(), rightNow.second());
  date = buffer;
}

void handleRoot() {
  String html = "<!DOCTYPE html>\r\n<html>\r\n\t<head><meta name='viewport' content='width=device-width, initial-scale=1.0'/><meta charset='utf-8'><style>body {font-size:140%;} #main {display: table; margin: auto;  padding: 0 10px 0 10px; } h2 {text-align:center; }</style><title>Aire Acondicionado</title></head>";
  html += "<body><div id='main'><p>Aire fijado a : ";
  html += String(temp);
  html += "C</p><p>Temperatura actual : ";
  html += String(t);
  html += "C</p><p>Humedad actual : ";
  html += String(h);
  html += "%</p><p>Salidas : ";
  html += compressorOn ? "COMP " : "";
  html += heatingOn ? "CALOR " : "";
  html += fanOn ? "VENT" : "";
  html += "</p><p>Hora actual : ";
  html += date;
  html += "</p></body></html>";
  server.send(200, "text/html", html);
}

void handleNotFound() {
  String message = "File Not Found\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  for (uint8_t i = 0; i < server.args(); i++) {
    message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
  }
  server.send(404, "text/plain", message);
}
