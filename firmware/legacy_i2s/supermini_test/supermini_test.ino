void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println();
  Serial.println("Boot successful");
  Serial.println("ESP32-S3");

  if (psramFound()) {
    Serial.println("PSRAM detected");
  } else {
    Serial.println("No PSRAM");
  }

  Serial.println("Setup complete");
}

void loop() {
  Serial.println("Alive");
  delay(1000);
}
