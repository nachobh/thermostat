// Termostato ESP8266 - ver ANALISIS_PCB_THERMOSTAT.md para el plan de PCB.
// Salidas reales del Eberle sustituido: borne 1 calefaccion, borne 3 ventilador
// y borne 4 compresor. Las cargas de 230 V las conmutan tres reles externos
// Hongfa HF115F/005-1ZS3 (bobina 5 V, 62 ohm, ~80 mA) alimentados desde USB/Vin:
// +5V -> bobina+, bobina- -> colector BC547B, emisor -> GND, con un diodo
// 1N4007/1N4148 en cada bobina (catodo a +5V). Cada base lleva 1k desde el GPIO
// y 10k a GND. Esta topologia mantiene D8/GPIO15 bajo durante el boot.
// Presupuesto de bobinas: F1 (RXEF030) retiene 0,30 A a 23 C y menos con calor,
// asi que como maximo DOS bobinas pueden estar activas a la vez (ver
// enforceCoilBudget); calefaccion y compresor nunca coinciden.
#include <Arduino.h>
#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <math.h>
#include <RTClib.h>
#include <stdlib.h>
#include <U8g2lib.h>
#include <WiFiClient.h>

#ifndef DHTTYPE
#define DHTTYPE DHT22
#endif
#define OLED_RESET -1
#ifdef __has_include
#if __has_include("Secrets.h")
#include "Secrets.h"
#endif
#endif
#ifndef STASSID
#define STASSID ""
#define STAPSK ""
#endif

const int POT_PIN = A0;
const int DHTPin = 14;     // D5 (GPIO14)
const int FAN_PIN = 12;        // D6 (GPIO12) -> Eberle 3 LOAD-FAN
const int COMPRESSOR_PIN = 13; // D7 (GPIO13) -> Eberle 4 LOAD-COMPRESSOR
const int HEATING_PIN = 15;    // D8 (GPIO15) -> Eberle 1 LOAD-HEATING
const int MENU_PIN = 0;    // D3 (GPIO0)
const int SELECT_PIN = 2;  // D4 (GPIO2)
const int CONTROL_PIN = 16;
const char* ssid = STASSID;
const char* password = STAPSK;

// Antiarranque del compresor: espera minima entre cualquier cambio termico y el
// siguiente encendido (5 min; el apagado nunca se retrasa). Tambien cuenta desde
// el arranque, de modo que tras un corte de red el compresor espera 5 min.
constexpr unsigned long THERMAL_CHANGE_MS = 300000UL;
constexpr uint8_t MAX_ENERGISED_COILS = 2;  // limite de F1 con calor: 2 x ~80 mA
constexpr unsigned long SENSOR_SAMPLE_MS = 2000UL;
constexpr unsigned long SENSOR_WINDOW_MS = 60000UL;
constexpr unsigned long WIFI_CONNECT_TIMEOUT_MS = 15000UL;
constexpr double SENSOR_OUTLIER_C = 2.0;
constexpr double CONTROL_HYSTERESIS_C = 0.5;
// Potenciometro de consigna en A0. Con USE_POT 0 (caja v6, solo pantalla) no se lee A0
// (flotaria y la consigna saltaria): la consigna arranca en DEFAULT_SETPOINT_C y solo
// cambia por orden remota (/temp) o, cuando se implemente, desde la pantalla tactil.
#ifndef USE_POT
#define USE_POT 1
#endif
constexpr double DEFAULT_SETPOINT_C = 21.0;
constexpr size_t SENSOR_SAMPLE_COUNT = 30;

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
double oldTemp = 0.00;
double valueRead = 0.00;
double t;
double h;
boolean controlOff = true;
boolean rtcAvailable = false;
boolean mdnsAvailable = false;
unsigned long lastThermalChangeMs = 0;
unsigned long lastSensorReadMs = 0;
unsigned long lastWifiAttemptMs = 0;
boolean remoteSetpointActive = false;
int lastPotReading = -1;

struct SensorSample {
  double temperature;
  double humidity;
  unsigned long timestamp;
};

SensorSample sensorSamples[SENSOR_SAMPLE_COUNT];
size_t sensorSampleHead = 0;
size_t sensorSampleSize = 0;
int yyyy, MM, dd, hh, mm, ss;

DateTime rightNow;
String date;

ESP8266WebServer server(80);
U8G2_SSD1306_128X64_NONAME_F_SW_I2C u8g2(U8G2_R0, /* clock=*/ SCL, /* data=*/ SDA, /* reset=*/ U8X8_PIN_NONE);
U8G2_SSD1306_128X64_NONAME_F_SW_I2C u8g2B(U8G2_R0, /* clock=*/ SCL, /* data=*/ SDA, /* reset=*/ U8X8_PIN_NONE);
DHT dht(DHTPin, DHTTYPE);
RTC_DS3231 rtc;

void setup() {
  // Fijar el latch antes de habilitar las salidas reduce pulsos durante el boot.
  digitalWrite(COMPRESSOR_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);
  digitalWrite(HEATING_PIN, LOW);
  pinMode(COMPRESSOR_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HEATING_PIN, OUTPUT);
  pinMode(POT_PIN, INPUT);
  pinMode(MENU_PIN, INPUT_PULLUP);
  pinMode(SELECT_PIN, INPUT_PULLUP);
  // GPIO16/D0 has no normal pull-up. The switch closes D0 to 3V3 when ON;
  // the PCB's 10k pull-down makes a disconnected cable default to OFF.
  pinMode(CONTROL_PIN, INPUT_PULLDOWN_16);

  Serial.begin(9600);

  startScreenA();
  startScreenB();
  startDht();
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

  mdnsAvailable = WiFi.status() == WL_CONNECTED && MDNS.begin("esp8266");
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

  server.begin();
  Serial.println("HTTP server started");

  // Conserva la espera de 300 s tras cada arranque antes de energizar una carga termica.
  lastThermalChangeMs = millis();
}

void loop() {

  controlOff = !digitalRead(CONTROL_PIN);

  if (controlOff) {

    u8g2B.clear();
    u8g2.clear();

    u8g2B.clearBuffer();
    u8g2.clearBuffer();

    fanForcedOn = false;
    fanForcedOff = false;
    heatingForcedOn = false;
    heatingForcedOff = false;
    compressorForcedOn = false;
    compressorForcedOff = false;

    allOutputsOffImmediate();

  } else {

    setTemp();
    boolean sensorAvailable = updateFilteredSensor();
    if (!sensorAvailable) {
      // Sin una medida valida del ultimo minuto, el unico fallback seguro es apagar.
      allOutputsOffImmediate();
    } else {

    u8g2B.clearBuffer();
    u8g2B.setCursor(5, 1);
    u8g2B.print(temp);
    u8g2B.sendBuffer();

    printTemp(temp);
    printT(t);
    printH(h);

    u8g2.setCursor(0, 40);

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
    } else if (fanForcedOff || (!fanForcedOn && !fanForcedOff)) {
      setFanOff();
    }

    enforceCoilBudget();

    printDate();

    u8g2.sendBuffer();
    }
  }

  server.handleClient();
  if (mdnsAvailable) {
    MDNS.update();
  }
  maintainWifi();
  delay(25);

}

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
  oldTemp = temp;
  temp = constrain(requestedTemperature, 15.0, 30.0);
  remoteSetpointActive = true;
  printTemp(temp);
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
    fanForcedOn = false;
    fanForcedOff = false;
    heatingForcedOn = false;
    heatingForcedOff = false;
    compressorForcedOn = false;
    compressorForcedOff = false;
    server.send(200, "text/plain", String("Establecido modo auto"));
  } else {
    server.send(400, "text/plain", String("Usa auto=true"));
  }
}

void startScreenA(void) {
  u8g2.setI2CAddress(0x7A);
  u8g2.begin();
  u8g2_prepare();
}

void startScreenB(void) {
  u8g2B.setI2CAddress(0x78);
  u8g2B.begin();
  u8g2B_prepare();
}

void startDht(void) {
  dht.begin();
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
      mdnsAvailable = MDNS.begin("esp8266");
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
  controlOff = !digitalRead(CONTROL_PIN);
  if (!controlOff) return true;
  server.send(409, "text/plain", "Control fisico OFF: orden rechazada");
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
  double measuredHumidity = dht.readHumidity();
  double measuredTemperature = dht.readTemperature();

  if (isnan(measuredHumidity) || isnan(measuredTemperature)) {
    Serial.println("DHT read failed; using the last-minute average");
  } else if (haveRecentAverage && fabs(measuredTemperature - averageTemperature) > SENSOR_OUTLIER_C) {
    Serial.println("DHT temperature outlier discarded");
  } else {
    addSensorSample(measuredTemperature, measuredHumidity);
    haveRecentAverage = recentSensorAverage(averageTemperature, averageHumidity);
  }

  if (!haveRecentAverage) return false;
  t = averageTemperature;
  h = averageHumidity;
  return true;
}

void u8g2_prepare(void) {
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.setFontRefHeightExtendedText();
  u8g2.setDrawColor(1);
  u8g2.setFontPosTop();
  u8g2.setFontDirection(0);
}

void u8g2B_prepare(void) {
  u8g2B.setFont(u8g2_font_logisoso42_tf);
  u8g2B.setFontRefHeightExtendedText();
  u8g2B.setDrawColor(1);
  u8g2B.setFontPosTop();
  u8g2B.setFontDirection(0);
}

void setTemp(void) {
#if !USE_POT
  if (temp == 0.0) {
    oldTemp = temp;
    temp = DEFAULT_SETPOINT_C;
  }
  return;
#endif
  int potReading = analogRead(POT_PIN);
  if (lastPotReading < 0) lastPotReading = potReading;
  if (remoteSetpointActive) {
    // Una orden web persiste hasta que el usuario mueva fisicamente el mando.
    if (abs(potReading - lastPotReading) <= 12) return;
    remoteSetpointActive = false;
  }
  lastPotReading = potReading;
  valueRead = (double)potReading;
  valueRead = valueRead <= 40 ? 0 : valueRead;
  double newTemp = round((18.0 + valueRead / 128.00) * 10) / 10;
  if (temp == 0.0 || fabs(temp - newTemp) > 0.4) {
    oldTemp = temp;
    temp = newTemp;
  }
}

void printTemp(double temp) {
  u8g2.clearBuffer();
  u8g2.setCursor(0, 10);
  u8g2.print("Aire fijado a ");
  u8g2.print(temp);
  u8g2.print("C");
  Serial.print("FixedTemp: ");
  Serial.print(temp);
}

void printT(double t) {
  u8g2.setCursor(0, 20);
  u8g2.print("Temperatura: ");
  u8g2.print(t);
  u8g2.print("C");
  Serial.print("Temperature: ");
  Serial.print(t);
}

void printH(double h) {
  u8g2.setCursor(0, 30);
  u8g2.print("Humedad: ");
  u8g2.print(h);
  u8g2.print("%");
  Serial.print("\tHumidity: ");
  Serial.print(h);
  Serial.print(" % \r\n");
}

uint8_t energisedCoils(void) {
  return (compressorOn ? 1 : 0) + (heatingOn ? 1 : 0) + (fanOn ? 1 : 0);
}

// Red de seguridad: calefaccion y compresor jamas a la vez, y nunca mas de
// MAX_ENERGISED_COILS bobinas activas (F1 + calor). Si se incumple, todo a OFF.
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
  if (compressorOn) {
    u8g2.print("COMP ON");
    return;
  }
  if (!thermalChangeAllowed()) {
    u8g2.print("COMP WAIT");
    return;
  }
  digitalWrite(HEATING_PIN, LOW);
  digitalWrite(COMPRESSOR_PIN, HIGH);
  heatingOn = false;
  compressorOn = true;
  lastThermalChangeMs = millis();
  u8g2.print("COMP ON");
}

void setCompressorOff(void) {
  if (!compressorOn) return;
  // La espera anticiclo sólo limita el próximo encendido, nunca el apagado.
  digitalWrite(COMPRESSOR_PIN, LOW);
  compressorOn = false;
  lastThermalChangeMs = millis();
  u8g2.print("COMP OFF");
}

void setHeatingOn(void) {
  if (heatingOn) {
    u8g2.print("HEAT ON");
    return;
  }
  if (!thermalChangeAllowed()) {
    u8g2.print("HEAT WAIT");
    return;
  }
  digitalWrite(COMPRESSOR_PIN, LOW);
  digitalWrite(HEATING_PIN, HIGH);
  compressorOn = false;
  heatingOn = true;
  lastThermalChangeMs = millis();
  u8g2.print("HEAT ON");
}

void setHeatingOff(void) {
  if (!heatingOn) return;
  // Una orden de apagado debe poder detener la carga inmediatamente.
  digitalWrite(HEATING_PIN, LOW);
  heatingOn = false;
  lastThermalChangeMs = millis();
  u8g2.print("HEAT OFF");
}

void setThermalOff(void) {
  if (!compressorOn && !heatingOn) return;
  digitalWrite(COMPRESSOR_PIN, LOW);
  digitalWrite(HEATING_PIN, LOW);
  compressorOn = false;
  heatingOn = false;
  lastThermalChangeMs = millis();
  u8g2.print("THERM OFF");
}

void setFanOn(void) {
  digitalWrite(FAN_PIN, HIGH);
  fanOn = true;
  u8g2.print(" - FAN ON");
}

void setFanOff(void) {
  // Una orden forzada de apagado no vence la ventilacion requerida por una carga termica.
  if (compressorOn || heatingOn) {
    setFanOn();
    return;
  }
  digitalWrite(FAN_PIN, LOW);
  fanOn = false;
  u8g2.print(" - FAN OFF");
}

void printDate(void) {
  u8g2.setCursor(0, 50);
  if (!rtcAvailable) {
    date = "UP ";
    date += String(millis() / 1000UL);
    date += "s";
    u8g2.print(date);
    return;
  }
  rightNow = rtc.now();
  date = fixNumber(rightNow.year());
  date += "-";
  date += fixNumber(rightNow.month());
  date += "-";
  date += fixNumber(rightNow.day());
  date += " ";
  date += fixNumber(rightNow.hour());
  date += ":";
  date += fixNumber(rightNow.minute());
  date += ":";
  date += fixNumber(rightNow.second());
  u8g2.print(date);
}

String fixNumber(int number) {
  switch (number) {
    case (0):
      return "00";
    case (1):
      return "01";
    case (2):
      return "02";
    case (3):
      return "03";
    case (4):
      return "04";
    case (5):
      return "05";
    case (6):
      return "06";
    case (7):
      return "07";
    case (8):
      return "08";
    case (9):
      return "09";
    default:
      return String(number);
  }
}

void handleRoot() {
  String html = "<!DOCTYPE html>\r\n<html>\r\n\t<head><meta name='viewport' content='width=device-width, initial-scale=1.0'/><meta charset='utf-8'><style>body {font-size:140%;} #main {display: table; margin: auto;  padding: 0 10px 0 10px; } h2 {text-align:center; }</style><title>Aire Acondicionado</title></head>";
  html += "<body><div id='main'><p>Aire fijado a : ";
  html += String(temp);
  html += "C</p><p>Temperatura actual : ";
  html += String(t);
  html += "C</p><p>Humedad actual : ";
  html += String(h);
  html += "%</p><p>Hora actual : ";
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
