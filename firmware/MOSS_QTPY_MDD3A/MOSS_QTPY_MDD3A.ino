// MOSS V0.4 - Adafruit QT Py ESP32-S3 (5426) on a Terminal Block BFF (6495),
// Cytron MDD3A dual motor driver, INA219 on the STEMMA QT port.
// Same serial protocol as the V0.3 DevKitC firmware (see ../README.md), over
// the QT Py's native USB: build with "USB CDC On Boot: Enabled"
// (arduino-cli: --fqbn esp32:esp32:adafruit_qtpy_esp32s3_nopsram:CDCOnBoot=cdc).
// Motors never start at boot. NOT YET RUN ON HARDWARE: pin map to confirm on the
// terminal block, then bench with "test left 10" before any "drive".
#include <Arduino.h>
#include <Wire.h>
#include <driver/gpio.h>
#include "Control.h"

// ── pin map (QT Py ESP32-S3 GPIO numbers, core 3.3.x variant) ────────────
// MDD3A: two PWM inputs per channel. A high / B low = forward, A low / B high
// = backward, both low = brake (datasheet table 3). Logic high 1.7-12 V, so
// 3.3 V is fine; PWM up to 20 kHz.
constexpr int M1A = A0;   // GPIO 18  left  forward PWM
constexpr int M1B = A1;   // GPIO 17  left  backward PWM
constexpr int M2A = A2;   // GPIO 9   right forward PWM
constexpr int M2B = A3;   // GPIO 8   right backward PWM
constexpr int ENC_L_A = SDA, ENC_L_B = SCL;   // GPIO 7 / 6 (primary I2C pins reused as inputs)
constexpr int ENC_R_A = TX,  ENC_R_B = RX;    // GPIO 5 / 16
// INA219 on the STEMMA QT connector = Wire1 (SDA1 = GPIO 41, SCL1 = GPIO 40)
constexpr uint8_t INA_ADDRESS = 0x40;
constexpr bool INVERT_LEFT = false, INVERT_RIGHT = false;
constexpr float SHUNT_OHMS = 0.0f;   // voltage only (see V0.3 README)
constexpr uint32_t PWM_HZ = 20000;
constexpr int PWM_BITS = 10;
constexpr const char* FW = "qtpy-mdd3a-v3";

moss::Control control;
moss::Ramp rampL, rampR;
bool pwmOK = false, inaOK = false, inaConfigured = false;
uint32_t lastTelemetry = 0, lastInaTry = 0;
int busMv = 0, shuntUv = 0;
volatile int64_t ticksL = 0, ticksR = 0;
volatile uint32_t badL = 0, badR = 0;
volatile uint8_t prevL = 0, prevR = 0;
portMUX_TYPE encoderMux = portMUX_INITIALIZER_UNLOCKED;
DRAM_ATTR const int8_t quadrature[16] = {0,-1,1,0,1,0,0,-1,-1,0,0,1,0,1,-1,0};

void ARDUINO_ISR_ATTR encoderLeft() {
  portENTER_CRITICAL_ISR(&encoderMux);
  uint8_t next = (gpio_get_level((gpio_num_t)ENC_L_A) << 1) | gpio_get_level((gpio_num_t)ENC_L_B);
  if ((prevL ^ next) == 3) badL = badL + 1;
  ticksL += quadrature[(prevL << 2) | next]; prevL = next;
  portEXIT_CRITICAL_ISR(&encoderMux);
}
void ARDUINO_ISR_ATTR encoderRight() {
  portENTER_CRITICAL_ISR(&encoderMux);
  uint8_t next = (gpio_get_level((gpio_num_t)ENC_R_A) << 1) | gpio_get_level((gpio_num_t)ENC_R_B);
  if ((prevR ^ next) == 3) badR = badR + 1;
  ticksR += quadrature[(prevR << 2) | next]; prevR = next;
  portEXIT_CRITICAL_ISR(&encoderMux);
}
void sendLine(const char* text) {
  // First hardware contact: the native CDC FIFO is 64 bytes, so a guard that required the
  // whole line to fit dropped every telemetry line (~330 bytes). write() already returns 0 when no
  // host has the port open (DTR low); with a 20 ms tx timeout a stalled host costs at most 20 ms per
  // line, which keeps the deadman (300 ms) serviced. A line cut by that timeout is the host's problem
  // (one bad JSON line), never the motors'.
  Serial.write((const uint8_t*)text, strlen(text)); Serial.write('\n');
}
void outputsZero() {
  if (pwmOK) { ledcWrite(M1A, 0); ledcWrite(M1B, 0); ledcWrite(M2A, 0); ledcWrite(M2B, 0); }
  else { digitalWrite(M1A, LOW); digitalWrite(M1B, LOW); digitalWrite(M2A, LOW); digitalWrite(M2B, LOW); }
  rampL.stop(millis()); rampR.stop(millis());
}
// MDD3A sign-magnitude: PWM on one input, the other held low. Zero = both low = brake.
void motorWrite(int pinA, int pinB, int percent, bool invert) {
  if (invert) percent = -percent;
  uint32_t duty = (uint32_t(abs(percent)) * 1023U) / 100U;
  if (percent > 0)      { ledcWrite(pinB, 0); ledcWrite(pinA, duty); }
  else if (percent < 0) { ledcWrite(pinA, 0); ledcWrite(pinB, duty); }
  else                  { ledcWrite(pinA, 0); ledcWrite(pinB, 0); }
}
bool readRegister(uint8_t reg, uint16_t& result) {
  Wire1.beginTransmission(INA_ADDRESS); Wire1.write(reg);
  if (Wire1.endTransmission(false) != 0) return false;
  if (Wire1.requestFrom(INA_ADDRESS, (uint8_t)2) != 2) return false;
  result = (uint16_t(Wire1.read()) << 8); result |= Wire1.read(); return true;
}
bool initIna() {
  Wire1.beginTransmission(INA_ADDRESS);
  Wire1.write((uint8_t)0x00); Wire1.write((uint8_t)0x39); Wire1.write((uint8_t)0x9F);
  if (Wire1.endTransmission() != 0) return false;
  uint16_t config;
  return readRegister(0x00, config) && config == 0x399F;
}
void updateIna(uint32_t now) {
  if (!inaConfigured) {
    if (uint32_t(now - lastInaTry) >= 1000) { lastInaTry = now; inaConfigured = initIna(); }
    return;
  }
  uint16_t bus, shunt;
  if (!readRegister(0x02, bus) || !readRegister(0x01, shunt)) { inaOK = false; inaConfigured = false; return; }
  inaOK = true;
  busMv = (bus >> 3) * 4;
  shuntUv = int16_t(shunt) * 10;
}
void telemetry() {
  int64_t l, r; uint32_t il, ir;
  portENTER_CRITICAL(&encoderMux);
  l = ticksL; r = ticksR; il = badL; ir = badR;
  portEXIT_CRITICAL(&encoderMux);
  char bus[24] = "null", shunt[24] = "null", current[32] = "null";
  if (inaOK) {
    snprintf(bus, sizeof(bus), "%d", busMv);
    snprintf(shunt, sizeof(shunt), "%d", shuntUv);
    if (SHUNT_OHMS > 0) snprintf(current, sizeof(current), "%.2f", shuntUv / (1000.0f * SHUNT_OHMS));
  }
  char out[560];
  snprintf(out, sizeof(out),
    "{\"ms\":%lu,\"fw\":\"%s\",\"mode\":%d,\"reason\":\"%s\",\"target_pct\":[%d,%d],\"output_pct\":[%d,%d],"
    "\"ramp_ms\":[%lu,%lu],\"ticks\":[%lld,%lld],\"invalid_edges\":[%lu,%lu],\"ina_ok\":%s,\"bus_mV\":%s,\"shunt_uV\":%s,\"current_mA\":%s}",
    (unsigned long)millis(), FW, int(control.mode), control.reason, control.left, control.right,
    rampL.sign*rampL.value, rampR.sign*rampR.value,
    (unsigned long)control.rampRiseMs, (unsigned long)control.rampFallMs,
    (long long)l, (long long)r, (unsigned long)il, (unsigned long)ir, inaOK ? "true" : "false", bus, shunt, current);
  sendLine(out);
}
void handleCommand(char* line) {
  if (!pwmOK) { control.stop("pwm_init_failed"); outputsZero(); sendLine("ERR pwm_init_failed"); return; }
  moss::Reply reply = control.command(line, millis());
  if (control.mode == moss::OFF || control.mode == moss::READY) outputsZero();
  if (reply == moss::ZERO) {
    portENTER_CRITICAL(&encoderMux); ticksL = 0; ticksR = 0; badL = 0; badR = 0; portEXIT_CRITICAL(&encoderMux);
  }
  if (reply == moss::STATUS) telemetry();
  else sendLine(reply == moss::INVALID ? "ERR invalid_command" : reply == moss::NOT_ARMED ? "ERR not_armed" : reply == moss::BUSY ? "ERR stopped_busy" : "OK");
}
void serviceSerial() {
  static char line[96]; static size_t used = 0;
  static bool discard = false; static uint32_t began = 0;
  if (used && uint32_t(millis() - began) >= 100) {
    used = 0; discard = true; control.stop("partial_line_timeout"); outputsZero();
  }
  for (int budget = 0; budget < 64 && Serial.available(); ++budget) {
    char c = char(Serial.read());
    if (c == '\r') continue;
    if (c == '\n') {
      if (!discard && used) { line[used] = 0; handleCommand(line); }
      used = 0; discard = false; continue;
    }
    if (discard) continue;
    if ((c < 32 && c != '\t') || c > 126 || used == sizeof(line)-1) {
      control.stop("serial_invalid"); outputsZero(); used = 0; discard = true; continue;
    }
    if (!used) began = millis();
    line[used++] = c;
  }
}
void setup() {
  for (int pin : {M1A, M1B, M2A, M2B}) { pinMode(pin, OUTPUT); digitalWrite(pin, LOW); }
  Serial.begin(115200);
  Serial.setTxTimeoutMs(20);  // native USB: bounded wait, see sendLine()
  bool ok = true;
  for (int pin : {M1A, M1B, M2A, M2B}) ok = ledcAttach(pin, PWM_HZ, PWM_BITS) && ok;
  pwmOK = ok;
  if (!pwmOK) {
    for (int pin : {M1A, M1B, M2A, M2B}) { ledcWrite(pin, 0); ledcDetach(pin); pinMode(pin, OUTPUT); digitalWrite(pin, LOW); }
    control.stop("pwm_init_failed");
  }
  outputsZero();
  for (int pin : {ENC_L_A, ENC_L_B, ENC_R_A, ENC_R_B}) pinMode(pin, INPUT_PULLUP);
  prevL = (digitalRead(ENC_L_A) << 1) | digitalRead(ENC_L_B);
  prevR = (digitalRead(ENC_R_A) << 1) | digitalRead(ENC_R_B);
  attachInterrupt(ENC_L_A, encoderLeft, CHANGE); attachInterrupt(ENC_L_B, encoderLeft, CHANGE);
  attachInterrupt(ENC_R_A, encoderRight, CHANGE); attachInterrupt(ENC_R_B, encoderRight, CHANGE);
  Wire1.begin(SDA1, SCL1, 100000); Wire1.setTimeOut(5);
  inaConfigured = initIna();
  { char banner[160]; snprintf(banner, sizeof(banner), "MOSS V0.4 firmware %s; USB CDC 115200; limit %d%%; ramp %lu/%lu ms per %%; type status",
    FW, moss::MAX_PERCENT, (unsigned long)control.rampRiseMs, (unsigned long)control.rampFallMs); sendLine(banner); }
}
void loop() {
  uint32_t now = millis();
  if (control.poll(now)) outputsZero();
  serviceSerial();
  now = millis();
  if (control.poll(now)) outputsZero();
  if (pwmOK && (control.mode == moss::DRIVE || control.mode == moss::TEST)) {
    motorWrite(M1A, M1B, rampL.tick(control.left, now, control.rampRiseMs, control.rampFallMs), INVERT_LEFT);
    motorWrite(M2A, M2B, rampR.tick(control.right, now, control.rampRiseMs, control.rampFallMs), INVERT_RIGHT);
  }
  if (uint32_t(now - lastTelemetry) >= 200) {
    lastTelemetry = now; updateIna(now); telemetry();
  }
  delay(1);
}
