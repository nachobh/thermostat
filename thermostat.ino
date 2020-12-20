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

#define DHTTYPE DHT22
#define OLED_RESET -1
#ifndef STASSID
  #define STASSID "MiFibra-7330"
  #define STAPSK "nyjLdSoanyjLdSoa"
#endif

const int POT_PIN = A0;
const int DHTPin = 14;
const int GREEN_PIN = 12;
const int RED_PIN = 13;
const int YELLOW_PIN = 15;
const char* ssid = STASSID;
const char* password = STAPSK;

boolean isTimeForAChange;
boolean hotOn;
boolean fanOn;

boolean fanForcedOn;
boolean fanForcedOff;
boolean hotForcedOn;
boolean hotForcedOff;
boolean coldForcedOn;
boolean coldForcedOff;

double temp = 0.00;
double oldTemp = 0.00;
double valueRead = 0.00;
double t;
double h;
int yyyy, MM, dd, hh, mm, ss;

DateTime rightNow;
DateTime lastChangeTime;
String date;

ESP8266WebServer server(80);
U8G2_SSD1306_128X64_NONAME_F_SW_I2C u8g2(U8G2_R0, /* clock=*/ SCL, /* data=*/ SDA, /* reset=*/ U8X8_PIN_NONE);
U8G2_SSD1306_128X64_NONAME_F_SW_I2C u8g2B(U8G2_R0, /* clock=*/ SCL, /* data=*/ SDA, /* reset=*/ U8X8_PIN_NONE);
DHT dht(DHTPin, DHTTYPE);
RTC_DS3231 rtc;

void setup() {

  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(YELLOW_PIN, OUTPUT);
  pinMode(POT_PIN, INPUT);

  Serial.begin(9600);

  startScreenA();
  startScreenB();
  startDht();
  startRtc();

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.println("");

  // Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  if (MDNS.begin("esp8266")) {
    Serial.println("MDNS responder started");
  }

  server.on("/", handleRoot);
  server.onNotFound(handleNotFound);
  server.on("/temp", HTTP_GET, getTemp);

  server.begin();
  Serial.println("HTTP server started");

  lastChangeTime = rtc.now();

}


void getTemp()
{
  oldTemp = temp;
  temp = server.arg(String("temp")).toDouble();
  printTemp(temp);
  server.send(200, "text/plain", String("Temperatura cambiada a " + String(temp)));
}

void loop() {

  isTimeForAChange = rtc.now().unixtime() - lastChangeTime.unixtime() >= 300;
  
  setTemp();

  delay(500);
  h = dht.readHumidity();
  t = dht.readTemperature();


  u8g2B.clearBuffer();
  u8g2B.setCursor(5, 1);
  u8g2B.print(temp);
  u8g2B.print(" C");
  u8g2B.sendBuffer();

  printTemp(temp);
  printT(t);
  printH(h);
  
  u8g2.setCursor(0, 40);
  if (coldForcedOn || (!hotForcedOn && !coldForcedOff && t - temp > 0)) {
    setColdOn();
  } else if (hotForcedOn || (!coldForcedOn && !hotForcedOff && t - temp < 0)) {
    setHotOn();
  }
  if (fanForcedOn || (t - temp >= 3 || t - temp <= -3 || ((t - temp >= 3 || t - temp <= -1) && h > 65))) {
    setFanOn();
  } else if (fanForcedOff || (!fanForcedOn && !fanForcedOff)) {
    setFanOff();
  }

  printDate();

  u8g2.sendBuffer();

  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  server.handleClient();
  MDNS.update();

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
    Serial.println(F("Couldn't find RTC"));
    while (1);
  }

  if (rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
}

void u8g2_prepare(void) {
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.setFontRefHeightExtendedText();
  u8g2.setDrawColor(1);
  u8g2.setFontPosTop();
  u8g2.setFontDirection(0);
}

void u8g2B_prepare(void) {
  u8g2B.setFont(u8g2_font_logisoso54_tf);
  u8g2B.setFontRefHeightExtendedText();
  u8g2B.setDrawColor(1);
  u8g2B.setFontPosTop();
  u8g2B.setFontDirection(0);
}

void setTemp(void) {
  valueRead = (double)analogRead(POT_PIN);
  valueRead = valueRead <= 40 ? 0 : valueRead;
  double newTemp = round((18.0 + valueRead / 128.00) * 10) / 10;
  boolean smallVariation = oldTemp - newTemp <= 0.4 && oldTemp - newTemp >= -0.4;
  temp = newTemp == 0.00 ? temp : smallVariation ? temp : newTemp;
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
  Serial.print(" %\t");
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
  Serial.print(" *C \r\n");
}

void setColdOn(void) {
  if (isTimeForAChange) {
    lastChangeTime = rtc.now();  
    digitalWrite(RED_PIN, HIGH);
    digitalWrite(YELLOW_PIN, LOW);
    digitalWrite(GREEN_PIN, LOW);
    u8g2.print("COLD ON");
    hotOn = false;
  } else if (hotOn) {
    u8g2.print("COLD STARTING");
  } else {
    u8g2.print("COLD ON");
  }
}

void setFanOn(void) {
  if (isTimeForAChange) {
    lastChangeTime = rtc.now();
    digitalWrite(GREEN_PIN, HIGH);
    u8g2.print(" - FAN ON");
    fanOn = true;
  } else if (!fanOn) {
    u8g2.print("- FAN STARTING");
  } else {
    u8g2.print(" - FAN ON");    
  }
}

void setFanOff(void) {
  if (isTimeForAChange) {
    lastChangeTime = rtc.now();
    digitalWrite(GREEN_PIN, LOW);
    u8g2.print(" - FAN OFF");
    fanOn = false;
  } else if (fanOn) {
    u8g2.print("- FAN STOPPING");
  } else {
    u8g2.print(" - FAN OFF");    
  }
}

void setHotOn(void) {
  if (isTimeForAChange) {
    lastChangeTime = rtc.now();
    digitalWrite(RED_PIN, LOW);
    digitalWrite(YELLOW_PIN, HIGH);
    digitalWrite(GREEN_PIN, LOW);
    u8g2.print("HOT ON");
    hotOn = true;
  } else if (!hotOn) {
    u8g2.print("HOT STARTING");
  } else {
    u8g2.print("HOT ON");
  }
}

void printDate(void) {
  u8g2.setCursor(0, 50);
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
