// MOSS V0.3 - ESP32-S3-DevKitC-1 V1.1, Arduino ESP32 core 3.x.
// Use the USB-to-UART connector, 115200 baud. Motors never start at boot.
#include <Arduino.h>
#include <Wire.h>
#include <driver/gpio.h>
#include "Control.h"

constexpr int PWM_L = 4, DIR_L = 5, PWM_R = 6, DIR_R = 7;
constexpr int ENC_L_A = 15, ENC_L_B = 16, ENC_R_A = 17, ENC_R_B = 18;
constexpr int SDA_PIN = 8, SCL_PIN = 9;
constexpr uint8_t INA_ADDRESS = 0x40; // Default A0/A1 configuration.
constexpr bool INVERT_LEFT = false, INVERT_RIGHT = false;
// Unknown until the actual module's shunt is identified. Zero disables current output.
constexpr float SHUNT_OHMS = 0.0f;
constexpr uint32_t PWM_HZ = 20000;
constexpr int PWM_BITS = 10;

moss::Control control;
moss::Ramp rampL, rampR;
bool pwmOK = false, inaOK = false, inaConfigured = false;
uint32_t lastTick = 0, lastTelemetry = 0, lastInaTry = 0;
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
  size_t n = strlen(text);
  // Drop a message rather than block motor/watchdog processing on a stalled host.
  if (Serial0.availableForWrite() >= int(n + 1)) {
    Serial0.write((const uint8_t*)text, n); Serial0.write('\n');
  }
}
void outputsZero() {
  if (pwmOK) { ledcWrite(PWM_L, 0); ledcWrite(PWM_R, 0); }
  else { digitalWrite(PWM_L, LOW); digitalWrite(PWM_R, LOW); }
  rampL.stop(millis()); rampR.stop(millis());
}
void motorWrite(int pwm, int dir, int percent, bool invert) {
  if (invert) percent = -percent;
  if (!percent) { ledcWrite(pwm, 0); return; }
  digitalWrite(dir, percent > 0 ? HIGH : LOW);
  ledcWrite(pwm, (uint32_t(abs(percent)) * 1023U) / 100U);
}
bool readRegister(uint8_t reg, uint16_t& result) {
  Wire.beginTransmission(INA_ADDRESS); Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(INA_ADDRESS, (uint8_t)2) != 2) return false;
  result = (uint16_t(Wire.read()) << 8); result |= Wire.read(); return true;
}
bool initIna() {
  Wire.beginTransmission(INA_ADDRESS);
  Wire.write((uint8_t)0x00); Wire.write((uint8_t)0x39); Wire.write((uint8_t)0x9F);
  if (Wire.endTransmission() != 0) return false;
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
  char out[512];
  snprintf(out, sizeof(out),
    "{\"ms\":%lu,\"mode\":%d,\"reason\":\"%s\",\"target_pct\":[%d,%d],\"output_pct\":[%d,%d],"
    "\"ticks\":[%lld,%lld],\"invalid_edges\":[%lu,%lu],\"ina_ok\":%s,\"bus_mV\":%s,\"shunt_uV\":%s,\"current_mA\":%s}",
    (unsigned long)millis(), int(control.mode), control.reason, control.left, control.right,
    rampL.sign*rampL.value, rampR.sign*rampR.value, (long long)l, (long long)r,
    (unsigned long)il, (unsigned long)ir, inaOK ? "true" : "false", bus, shunt, current);
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
  // Bound work per loop: sustained serial traffic cannot starve the watchdog.
  for (int budget = 0; budget < 64 && Serial0.available(); ++budget) {
    char c = char(Serial0.read());
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
  pinMode(PWM_L, OUTPUT); pinMode(PWM_R, OUTPUT);
  digitalWrite(PWM_L, LOW); digitalWrite(PWM_R, LOW);
  pinMode(DIR_L, OUTPUT); pinMode(DIR_R, OUTPUT);
  digitalWrite(DIR_L, LOW); digitalWrite(DIR_R, LOW);
  Serial0.setRxBufferSize(256); Serial0.setTxBufferSize(1024); Serial0.begin(115200);
  bool okL = ledcAttach(PWM_L, PWM_HZ, PWM_BITS);
  bool okR = ledcAttach(PWM_R, PWM_HZ, PWM_BITS);
  pwmOK = okL && okR;
  if (!pwmOK) {
    if (okL) { ledcWrite(PWM_L, 0); ledcDetach(PWM_L); }
    if (okR) { ledcWrite(PWM_R, 0); ledcDetach(PWM_R); }
    pinMode(PWM_L, OUTPUT); pinMode(PWM_R, OUTPUT); control.stop("pwm_init_failed");
  }
  outputsZero();
  for (int pin : {ENC_L_A, ENC_L_B, ENC_R_A, ENC_R_B}) pinMode(pin, INPUT_PULLUP);
  prevL = (digitalRead(ENC_L_A) << 1) | digitalRead(ENC_L_B);
  prevR = (digitalRead(ENC_R_A) << 1) | digitalRead(ENC_R_B);
  attachInterrupt(ENC_L_A, encoderLeft, CHANGE); attachInterrupt(ENC_L_B, encoderLeft, CHANGE);
  attachInterrupt(ENC_R_A, encoderRight, CHANGE); attachInterrupt(ENC_R_B, encoderRight, CHANGE);
  Wire.begin(SDA_PIN, SCL_PIN, 100000); Wire.setTimeOut(5);
  inaConfigured = initIna();
  sendLine("MOSS V0.3 bench firmware; USB-UART 115200; limit 25%; type status");
}
void loop() {
  uint32_t now = millis();
  if (control.poll(now)) outputsZero();
  serviceSerial();
  now = millis();
  if (control.poll(now)) outputsZero();
  if (pwmOK && uint32_t(now - lastTick) >= 10) {
    lastTick = now;
    if (control.mode == moss::DRIVE || control.mode == moss::TEST) {
      motorWrite(PWM_L, DIR_L, rampL.tick(control.left, now), INVERT_LEFT);
      motorWrite(PWM_R, DIR_R, rampR.tick(control.right, now), INVERT_RIGHT);
    }
  }
  if (uint32_t(now - lastTelemetry) >= 200) {
    lastTelemetry = now; updateIna(now); telemetry();
  }
  delay(1);
}
