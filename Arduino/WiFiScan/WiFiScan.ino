#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

#define DHTPIN 19       // Pin output data sensor DHT11
#define DHTTYPE DHT11   // Jenis sensor DHT yang digunakan
#define LEDPIN 22       // Pin LED eksternal pada ESP32
#define POWERPIN 23     // Pin untuk sumber tegangan
#define SMOKESENSOR 34  // Pin input data sensor MQ135

DHT dht(DHTPIN, DHTTYPE);

const char* ssid = "Sukses Bersama";
const char* password = "berjuang3";
const char* serverName = "http://192.168.1.44:5000/"; // Ganti dengan alamat IP server Python

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(LEDPIN, OUTPUT);
  pinMode(POWERPIN, OUTPUT);
  digitalWrite(LEDPIN, LOW);
  digitalWrite(POWERPIN, HIGH); // Nyalakan sumber tegangan untuk LED eksternal
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Connected to WiFi");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    int sensorValue = analogRead(SMOKESENSOR);
    int airQuality = map(sensorValue, 0, 4095, 1, 100);

    bool isIdeal = true;
    String message = "";

    if (isnan(temperature) || isnan(humidity) || isnan(sensorValue)) {
      Serial.println("Failed to read from sensors!");
      return;
    }

    // Check temperature
    if (temperature < 23.0) {
      isIdeal = false;
      message += "Suhu udara rendah; ";
    } else if (temperature > 35.0) {
      isIdeal = false;
      message += "Suhu udara tinggi; ";
    }

    // Check humidity
    if (humidity < 50.0) {
      isIdeal = false;
      message += "Kelembapan udara rendah; ";
    } else if (humidity > 88.0) {
      isIdeal = false;
      message += "Kelembapan udara tinggi; ";
    }

    // Check air quality
    if (airQuality >= 50) {
      isIdeal = false;
      message += "Kualitas udara buruk; ";
    }

    // Blink LED if not ideal (non-blocking)
    if (!isIdeal) {
      digitalWrite(LEDPIN, millis() % 1000 < 500 ? HIGH : LOW);  // LED berkedip tanpa blocking
    } else {
      digitalWrite(LEDPIN, LOW); // Matikan LED jika kondisi ideal
    }

    // Display readings
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" *C");

    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.println(" %");

    Serial.print("Air Quality: ");
    Serial.println(airQuality);

    // Send data to server
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    String postData = "{\"temperature\":" + String(temperature, 2) + ", \"humidity\":" + String(humidity, 2) + ", \"air_quality\":" + String(airQuality) + ", \"message\":\"" + message + "\"}";

    int httpResponseCode = http.POST(postData);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println(httpResponseCode);
      Serial.println(response);
    } else {
      Serial.print("Error on sending POST: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("Error in WiFi connection");
  }

  delay(1000);  // Delay 1 detik untuk loop utama
}
