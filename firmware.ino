/* =========================================================================
   🚆 RailSense — ESP32 Axle Telemetry & Predictive Integrity Node
   Firmware for ESP32-WROOM-32E + SX1276 LoRa + MPU6050 Accelerometer + OLED
   ========================================================================= */

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <RH_RF95.h>

// --- PIN DEFINITIONS ---
#define LORA_SS      5
#define LORA_RST     14
#define LORA_DIO0    2
#define BUZZER_PIN   12
#define STATUS_LED   15
#define BTN_ACK      39  // Button to acknowledge alarms

#define RF95_FREQ    868.0

// --- OLED CONFIGURATION ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- TELEMETRY PACKET STRUCTURE ---
struct __attribute__((__packed__)) RailSensePacket {
    uint16_t train_no;      // Indian Railways train number (e.g., 12301)
    uint32_t timestamp;     // Node runtime millisecond tick
    float speed_kmh;        // Measured or target velocity
    float vibration_g;      // RMS vibration level (G-force)
    float rail_temp_c;      // Ambient/rail track temperature
    uint8_t alarm_active;   // 0 = Nominal, 1 = Speed Restricted, 2 = Critical Buckling Risk
};

// --- GLOBAL VARIABLES ---
RH_RF95 rf95(LORA_SS, LORA_DIO0);
RailSensePacket telemetry;
bool local_alarm = false;
uint32_t last_transmission = 0;

// --- FreeRTOS Task Handles ---
TaskHandle_t DisplayTaskHandle = NULL;
TaskHandle_t TelemetryTaskHandle = NULL;

// --- TASK: Update Locomotive Cabin OLED Screen (Core 0) ---
void DisplayTask(void *pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(200); // 5Hz screen refresh

    Serial.println("[HUD] OLED Cabin Display task active.");

    while (true) {
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);

        // Draw HUD Header
        display.setCursor(0, 0);
        display.printf("RAILSENSE HUD - T#%d", telemetry.train_no);
        display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

        // Draw Telemetry Values
        display.setCursor(0, 15);
        display.printf("SPEED:   %.1f km/h", telemetry.speed_kmh);

        display.setCursor(0, 27);
        display.printf("VIB:     %.2fg", telemetry.vibration_g);

        display.setCursor(0, 39);
        display.printf("TEMP:    %.1f C", telemetry.rail_temp_c);

        // Draw Status Bar at bottom
        display.drawFastHLine(0, 52, 128, SSD1306_WHITE);
        display.setCursor(0, 56);
        if (local_alarm) {
            display.setTextColor(SSD1306_BLACK, SSD1306_WHITE); // Invert display for flashing alarm
            if (telemetry.alarm_active == 1) {
                display.print(" ALERT: SPEED RESTRICT ");
            } else {
                display.print(" CRIT: EXCESSIVE VIB  ");
            }
        } else {
            display.print("STATUS: COGNITIVE SAFE");
        }

        display.display();
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

// --- TASK: Telemetry Collector & LoRa Transmitter (Core 1) ---
void TelemetryTask(void *pvParameters) {
    Serial.println("[SYS] Telemetry processing engine active.");

    while (true) {
        // Read simulated/real MPU6050 accelerometer values
        // In physical deployment, raw X-Y-Z accelerometer registers are polled here:
        // float ax = readRawAccel(0x3B);
        // telemetry.vibration_g = calculateRMS(ax, ay, az);
        
        // Simulating vibration profile with periodic anomaly surges
        float base_vib = 0.08 + (random(0, 100) / 1000.0);
        if (random(0, 100) < 3) {
            telemetry.vibration_g = 0.48 + (random(0, 20) / 100.0); // Anomaly spike
        } else {
            telemetry.vibration_g = base_vib;
        }

        // Check for vibration exceptions
        if (telemetry.vibration_g > 0.45) {
            telemetry.alarm_active = 2; // Critical Vibration Alert
            local_alarm = true;
            digitalWrite(STATUS_LED, HIGH);
            digitalWrite(BUZZER_PIN, HIGH);
        } else if (telemetry.alarm_active == 0) {
            local_alarm = false;
            digitalWrite(STATUS_LED, LOW);
            digitalWrite(BUZZER_PIN, LOW);
        }

        // Transmit packet over LoRa every 1000ms
        if (millis() - last_transmission >= 1000) {
            telemetry.timestamp = millis();
            
            rf95.send((uint8_t *)&telemetry, sizeof(telemetry));
            rf95.waitPacketSent();
            last_transmission = millis();
            
            Serial.printf("[TX] Packet sent. Speed=%.1f, Vib=%.2fg, Temp=%.1fC\n", 
                          telemetry.speed_kmh, telemetry.vibration_g, telemetry.rail_temp_c);
        }

        // Listen for downlink commands from the Safety Command Center
        uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
        uint8_t len = sizeof(buf);
        if (rf95.available()) {
            if (rf95.recv(buf, &len)) {
                // If the command center restricts speed, parse command JSON/binary
                if (len > 0) {
                    char command[RH_RF95_MAX_MESSAGE_LEN];
                    memcpy(command, buf, len);
                    command[len] = '\0';
                    
                    if (strstr(command, "RestrictSpeed") != NULL) {
                        telemetry.alarm_active = 1; // Speed restricted by coordinator
                        telemetry.speed_kmh = 50.0; // Enforce limit on governor
                        local_alarm = true;
                        
                        // Triple short pulse buzzer to alert the pilot
                        for (int i = 0; i < 3; i++) {
                            digitalWrite(BUZZER_PIN, HIGH);
                            delay(80);
                            digitalWrite(BUZZER_PIN, LOW);
                            delay(80);
                        }
                    }
                }
            }
        }

        // Acknowledge button check
        if (digitalRead(BTN_ACK) == LOW) {
            if (telemetry.alarm_active == 1) {
                // Acknowledge limit restriction
                telemetry.alarm_active = 0;
                local_alarm = false;
                Serial.println("[ACK] Pilot acknowledged speed limit enforcement.");
            }
            delay(200); // Debounce
        }

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void setup() {
    Serial.begin(115200);

    // Pin Configurations
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(STATUS_LED, OUTPUT);
    pinMode(BTN_ACK, INPUT_PULLUP);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(STATUS_LED, LOW);

    // Initialize SSD1306 OLED HUD
    Wire.begin(21, 22);
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        Serial.println("[ERROR] Failed to initialize OLED Display.");
        while (1);
    }

    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(10, 24);
    display.println("BOOTING RAILSENSE...");
    display.display();

    // Initialize SX1276 LoRa Transceiver
    pinMode(LORA_RST, OUTPUT);
    digitalWrite(LORA_RST, HIGH);
    delay(10);
    digitalWrite(LORA_RST, LOW);
    delay(10);
    digitalWrite(LORA_RST, HIGH);
    delay(10);

    if (!rf95.init()) {
        Serial.println("[ERROR] LoRa transceiver initialization failed.");
        while (1);
    }

    if (!rf95.setFrequency(RF95_FREQ)) {
        Serial.println("[ERROR] Failed to lock LoRa frequency.");
        while (1);
    }

    rf95.setTxPower(23, false); // Maximum transmit power
    Serial.printf("[SYS] Axle Telemetry Node online at %.1f MHz.\n", RF95_FREQ);

    // Initial Telemetry Setup
    telemetry.train_no = 12301; // Default Howrah Rajdhani Express
    telemetry.speed_kmh = 110.0;
    telemetry.vibration_g = 0.12;
    telemetry.rail_temp_c = 42.5;
    telemetry.alarm_active = 0;

    // Create Dual-Core Tasks
    xTaskCreatePinnedToCore(
        DisplayTask,
        "DisplayTask",
        4096,
        NULL,
        2,
        &DisplayTaskHandle,
        0 // Core 0: OLED presentation UI
    );

    xTaskCreatePinnedToCore(
        TelemetryTask,
        "TelemetryTask",
        4096,
        NULL,
        3,
        &TelemetryTaskHandle,
        1 // Core 1: RF95 transceiver + accelerometer sampling
    );
}

void loop() {
    // Empty loop since we run FreeRTOS scheduling
}
