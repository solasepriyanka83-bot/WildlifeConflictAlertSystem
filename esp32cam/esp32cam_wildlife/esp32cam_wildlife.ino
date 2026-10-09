/*
  esp32cam_wildlife.ino
  ----------------------------------------------------------
  ESP32-CAM + PIR Motion Sensor -> WildSense Flask Server

  Wiring (typical AI-Thinker ESP32-CAM board):
    PIR OUT  -> GPIO 13
    LED      -> GPIO 12  (through resistor)
    Buzzer   -> GPIO 15  (through resistor / transistor if needed)
    Camera pins are on-board (AI-Thinker default pinout, see camera_pins below)

  Flow:
    PIR detects motion -> capture JPEG frame -> HTTP POST multipart
    to http://<SERVER_IP>:5000/api/detect (field name "image")
    -> LED + buzzer pulse to indicate a capture was sent.

  NOTE: This sketch is provided ready-to-flash. Update WIFI_SSID,
  WIFI_PASSWORD and SERVER_IP for your network before uploading.
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

#define PIR_PIN     13
#define LED_PIN     12
#define BUZZER_PIN  15

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_IP     = "192.168.1.100";   // <-- your Flask server's LAN IP
const int   SERVER_PORT   = 5000;
const char* LOCATION_TAG  = "Main Gate - Zone A";

// AI-Thinker ESP32-CAM pin map
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  connectWiFi();
  initCamera();
}

void loop() {
  if (digitalRead(PIR_PIN) == HIGH) {
    Serial.println("[PIR] Motion detected -> capturing frame");
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb) {
      bool ok = sendImageToServer(fb);
      esp_camera_fb_return(fb);
      if (ok) pulseAlert();
    } else {
      Serial.println("[CAM] Capture failed");
    }
    delay(4000); // debounce so one motion event doesn't spam multiple captures
  }
  delay(200);
}

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected, IP: " + WiFi.localIP().toString());
}

void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed");
  }
}

bool sendImageToServer(camera_fb_t* fb) {
  HTTPClient http;
  String url = "http://" + String(SERVER_IP) + ":" + String(SERVER_PORT) + "/api/detect";
  http.begin(url);

  String boundary = "WildSenseBoundary";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  String head = "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"location\"\r\n\r\n" +
                String(LOCATION_TAG) + "\r\n" +
                "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"image\"; filename=\"capture.jpg\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  uint32_t totalLen = head.length() + fb->len + tail.length();
  uint8_t* body = (uint8_t*)malloc(totalLen);
  memcpy(body, head.c_str(), head.length());
  memcpy(body + head.length(), fb->buf, fb->len);
  memcpy(body + head.length() + fb->len, tail.c_str(), tail.length());

  int code = http.POST(body, totalLen);
  free(body);
  Serial.printf("[HTTP] /api/detect response: %d\n", code);
  http.end();
  return code == 200;
}

void pulseAlert() {
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(600);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
}
