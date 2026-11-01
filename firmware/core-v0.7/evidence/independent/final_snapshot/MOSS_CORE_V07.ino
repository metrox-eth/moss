// SPDX-License-Identifier: Apache-2.0
// MOSS Core V0.7 commissioning firmware. Private candidate; no hardware
// qualification claimed.
#include "Core.h"
#include "Pins.h"
#include "Sensors.h"
#include "ServoBus.h"
#include <Arduino.h>
#include <USB.h>
#include <Wire.h>
#include <driver/gpio.h>
#include <driver/i2s_std.h>
#include <esp_bt.h>
#include <esp_system.h>
#include <esp_wifi.h>
#include <math.h>
#include <tusb.h>
#if ARDUINO_USB_MODE != 0 || ARDUINO_USB_CDC_ON_BOOT != 1
#error "Use native USB-OTG TinyUSB with CDCOnBoot=cdc"
#endif
using namespace core07;
Safety safety;
Lines rx;
Sensors sensors;
Watchdog watchdog;
ServoBus servo;
moss::Ramp rampL, rampR;
bool pwmOK = false, usbWasOpen = false, rxPurge = false;
uint32_t appliedGeneration = 0, lastTelemetry = 0, lastLoopUs = 0,
         maxLoopUs = 0, seenGeneration = 0;
volatile bool usbOverflow = false, encodersReady = false;
bool encoderPower = false;
uint32_t encoderPowerAt = 0;
volatile int64_t ticksL = 0, ticksR = 0;
volatile uint32_t badL = 0, badR = 0;
volatile uint8_t prevL = 0, prevR = 0;
portMUX_TYPE encoderMux = portMUX_INITIALIZER_UNLOCKED;
DRAM_ATTR const int8_t quadrature[16] = {0,  -1, 1, 0, 1, 0, 0,  -1,
                                         -1, 0,  0, 1, 0, 1, -1, 0};
void ARDUINO_ISR_ATTR encoderLeft() {
  if (!encodersReady)
    return;
  portENTER_CRITICAL_ISR(&encoderMux);
  uint8_t n = (gpio_get_level((gpio_num_t)pins::ENC_L_A) << 1) |
              gpio_get_level((gpio_num_t)pins::ENC_L_B);
  if ((prevL ^ n) == 3)
    badL = badL + 1;
  ticksL -= quadrature[(prevL << 2) | n];
  prevL = n;
  portEXIT_CRITICAL_ISR(&encoderMux);
}
void ARDUINO_ISR_ATTR encoderRight() {
  if (!encodersReady)
    return;
  portENTER_CRITICAL_ISR(&encoderMux);
  uint8_t n = (gpio_get_level((gpio_num_t)pins::ENC_R_A) << 1) |
              gpio_get_level((gpio_num_t)pins::ENC_R_B);
  if ((prevR ^ n) == 3)
    badR = badR + 1;
  ticksR += quadrature[(prevR << 2) | n];
  prevR = n;
  portEXIT_CRITICAL_ISR(&encoderMux);
}
struct I2CBus {
  bool read(uint8_t address, uint8_t reg, uint16_t &value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0)
      return false;
    if (Wire.requestFrom(address, uint8_t(2)) != 2)
      return false;
    value = uint16_t(Wire.read()) << 8;
    value |= Wire.read();
    return true;
  }
  bool write(uint8_t address, uint8_t reg, uint16_t value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(uint8_t(value >> 8));
    Wire.write(uint8_t(value));
    return Wire.endTransmission() == 0;
  }
} i2c;
// Nonblocking USB output: bounded queue, 64 bytes maximum per loop. Never wait
// for a reader.
char txQueue[4096]{};
size_t txHead = 0, txTail = 0;
uint32_t txDrops = 0;
void sendLine(const char *s) {
  size_t n = strlen(s);
  size_t free = (txTail + sizeof(txQueue) - txHead - 1) % sizeof(txQueue);
  if (n + 1 > free) {
    ++txDrops;
    return;
  }
  for (size_t j = 0; j < n; j++) {
    txQueue[txHead] = s[j];
    txHead = (txHead + 1) % sizeof(txQueue);
  }
  txQueue[txHead] = '\n';
  txHead = (txHead + 1) % sizeof(txQueue);
}
void serviceTx() {
  if (!Serial) {
    txHead = txTail = 0;
    return;
  }
  size_t n = (txHead + sizeof(txQueue) - txTail) % sizeof(txQueue);
  if (n > 64)
    n = 64;
  if (n > sizeof(txQueue) - txTail)
    n = sizeof(txQueue) - txTail;
  // Core 3.2.0 USBCDC::write can spin when its FIFO is full even with
  // timeout=0. TinyUSB's single write returns the accepted count; no retry and
  // no host-dependent wait.
  if (n) {
    uint32_t accepted = tud_cdc_n_write(0, txQueue + txTail, n);
    txTail = (txTail + accepted) % sizeof(txQueue);
    tud_cdc_n_write_flush(0);
  }
}
bool usbOpen() { return bool(Serial) && tud_mounted() && !tud_suspended(); }
Inputs inputs() {
  return {usbOpen(),
          bool(digitalRead(pins::ESTOP_ACTIVE)),
          !bool(digitalRead(pins::USB_PWR_FAULT_N)),
          bool(digitalRead(pins::ACT_READY)),
          bool(digitalRead(pins::ARM_LATCHED)),
          bool(digitalRead(pins::DRIVE_RUN)),
          pwmOK};
}
i2s_chan_handle_t audio = nullptr;
bool audioOK = false, toneActive = false;
uint32_t toneAt = 0, toneMs = 0, tonePhase = 0, toneHz = 440, toneAmplitude = 0;
void audioStop() {
  digitalWrite(pins::AUDIO_ENABLE, LOW);
  toneActive = false;
}
bool audioInit() {
  i2s_chan_config_t ch =
      I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
  ch.dma_desc_num = 4;
  ch.dma_frame_num = 128;
  ch.auto_clear = true;
  if (i2s_new_channel(&ch, &audio, nullptr) != ESP_OK)
    return false;
  i2s_std_config_t cfg{};
  cfg.clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(16000);
  cfg.slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                     I2S_SLOT_MODE_STEREO);
  cfg.gpio_cfg.mclk = I2S_GPIO_UNUSED;
  cfg.gpio_cfg.bclk = (gpio_num_t)pins::AUDIO_BCLK;
  cfg.gpio_cfg.ws = (gpio_num_t)pins::AUDIO_LRCLK;
  cfg.gpio_cfg.dout = (gpio_num_t)pins::AUDIO_DATA;
  cfg.gpio_cfg.din = I2S_GPIO_UNUSED;
  return i2s_channel_init_std_mode(audio, &cfg) == ESP_OK &&
         i2s_channel_enable(audio) == ESP_OK;
}
void audioPoll(uint32_t now) {
  if (!toneActive)
    return;
  if (uint32_t(now - toneAt) >= toneMs || !usbOpen()) {
    audioStop();
    return;
  }
  int16_t pcm[128 * 2];
  uint32_t phase = tonePhase;
  for (unsigned j = 0; j < 128; j++) {
    int16_t v = int16_t(sinf(float(phase) * 6.28318530718f / 16000.0f) *
                        float(toneAmplitude));
    pcm[2 * j] = pcm[2 * j + 1] = v;
    phase = (phase + toneHz) % 16000;
  }
  size_t written = 0;
  esp_err_t result = i2s_channel_write(audio, pcm, sizeof(pcm), &written, 0);
  tonePhase = (tonePhase + uint32_t(written / 4) * toneHz) % 16000;
  if (result != ESP_OK && result != ESP_ERR_TIMEOUT) {
    audioStop();
    sendLine("ERR audio_write");
  }
}
bool gateExpected = false;
uint32_t gateChanged = 0;
uint8_t servoStage = 0,
        servoId = 0; // torque-on: read current -> write goal -> torque enable
void zeroOutputs() {
  digitalWrite(pins::DRIVE_ENABLE, LOW);
  digitalWrite(pins::SERVO_TX_ENABLE, LOW);
  digitalWrite(pins::ARM_COMMIT, LOW);
  digitalWrite(pins::ACT_POWER_ENABLE, LOW);
  if (pwmOK) {
    ledcWrite(pins::PWM_L, 0);
    ledcWrite(pins::PWM_R, 0);
  } else {
    digitalWrite(pins::PWM_L, LOW);
    digitalWrite(pins::PWM_R, LOW);
  }
  digitalWrite(pins::DIR_L, LOW);
  digitalWrite(pins::DIR_R, LOW);
  rampL.stop(millis());
  rampR.stop(millis());
}
void applyStop() {
  zeroOutputs();
  servo.abort();
  servoStage = 0;
  audioStop();
  rx.reset();
  rxPurge = true;
  appliedGeneration = safety.generation;
}
void fault(const char *reason) {
  safety.stop(reason);
  applyStop();
}
void applySafety(uint32_t now) {
  Inputs in = inputs();
  if ((in.estop || in.usbFault) && toneActive)
    audioStop();
  safety.poll(now, in);
  if (gateExpected != safety.driveEnable()) {
    gateExpected = safety.driveEnable();
    gateChanged = now;
  } else if (uint32_t(now - gateChanged) >= 2 && in.driveRun != gateExpected) {
    if (safety.active() || strcmp(safety.reason, "drive_gate_mismatch"))
      fault("drive_gate_mismatch");
  }
  if (appliedGeneration != safety.generation)
    applyStop();
  digitalWrite(pins::ACT_POWER_ENABLE, safety.power());
  digitalWrite(pins::ARM_COMMIT, safety.commit());
  if (!safety.driveEnable()) {
    digitalWrite(pins::DRIVE_ENABLE, LOW);
    if (pwmOK) {
      ledcWrite(pins::PWM_L, 0);
      ledcWrite(pins::PWM_R, 0);
    }
    rampL.stop(now);
    rampR.stop(now);
  } else {
    int l = rampL.tick(safety.left, now, safety.rampUp, safety.rampDown),
        r = rampR.tick(safety.right, now, safety.rampUp, safety.rampDown);
    digitalWrite(pins::DIR_L, l < 0);
    digitalWrite(pins::DIR_R, r < 0);
    ledcWrite(pins::PWM_L, uint32_t(abs(l)) * 1023 / 100);
    ledcWrite(pins::PWM_R, uint32_t(abs(r)) * 1023 / 100);
    digitalWrite(pins::DRIVE_ENABLE, HIGH);
  }
}
void sampleText(const Sample &s, uint32_t now, char *out, size_t cap) {
  if (s.fresh(now))
    snprintf(out, cap, "%.4f", s.value);
  else
    snprintf(out, cap, "null");
}
void telemetry() {
  uint32_t now = millis();
  int64_t l, r;
  uint32_t il, ir;
  portENTER_CRITICAL(&encoderMux);
  l = ticksL;
  r = ticksR;
  il = badL;
  ir = badR;
  portEXIT_CRITICAL(&encoderMux);
  char b[24], ground[24], rail[24], cl[24] = "null", cr[24] = "null", al[24],
                                    ar[24];
  sampleText(sensors.battery, now, b, sizeof(b));
  sampleText(sensors.analog[2], now, rail, sizeof(rail));
  sampleText(sensors.analog[3], now, ground, sizeof(ground));
  sampleText(sensors.analog[0], now, al, sizeof(al));
  sampleText(sensors.analog[1], now, ar, sizeof(ar));
  float amps;
  if (current(sensors.analog[0], sensors.analog[2], now, amps))
    snprintf(cl, sizeof(cl), "%.4f", amps);
  if (current(sensors.analog[1], sensors.analog[2], now, amps))
    snprintf(cr, sizeof(cr), "%.4f", amps);
  Inputs in = inputs();
  char out[1100];
  snprintf(
      out, sizeof(out),
      "{\"ms\":%lu,\"fw\":\"core-v07-commissioning-1\",\"driver\":\"mdd10a\","
      "\"state\":%u,\"reason\":\"%s\",\"arm_token\":%lu,\"generation\":%lu,"
      "\"target_pct\":[%d,%d],\"output_pct\":[%d,%d],\"ramp_ms\":[%lu,%lu],"
      "\"ticks\":[%lld,%lld],\"invalid_edges\":[%lu,%lu],\"usb\":%s,\"act_"
      "ready\":%s,\"arm_latched\":%s,\"drive_run\":%s,\"estop\":%s,\"usb_power_"
      "fault\":%s,\"battery_V\":%s,\"rail_V\":%s,\"adc_ground_V\":%s,\"sense_"
      "V\":[%s,%s],\"current_"
      "A\":[%s,%s],\"i2c_errors\":%lu,\"servo_busy\":%s,\"audio_ok\":%s,"
      "\"tone\":%s,\"max_loop_us\":%lu,\"tx_drops\":%lu}",
      (unsigned long)now, unsigned(safety.state), safety.reason,
      (unsigned long)safety.token, (unsigned long)safety.generation,
      safety.left, safety.right, rampL.value * rampL.sign,
      rampR.value * rampR.sign, (unsigned long)safety.rampUp,
      (unsigned long)safety.rampDown, (long long)l, (long long)r,
      (unsigned long)il, (unsigned long)ir, in.usb ? "true" : "false",
      in.ready ? "true" : "false", in.latch ? "true" : "false",
      in.driveRun ? "true" : "false", in.estop ? "true" : "false",
      in.usbFault ? "true" : "false", b, rail, ground, al, ar, cl, cr,
      (unsigned long)sensors.errors, servo.busy ? "true" : "false",
      audioOK ? "true" : "false", toneActive ? "true" : "false",
      (unsigned long)maxLoopUs, (unsigned long)txDrops);
  sendLine(out);
}
bool num(const char *s, long lo, long hi, long &v) {
  return moss::Control::number(s, lo, hi, v);
}
bool servoRead(uint8_t id, uint8_t reg, uint8_t length) {
  uint8_t p[] = {reg, length};
  return servo.start(id, 2, p, 2, length, millis());
}
bool servoWrite(uint8_t id, uint8_t reg, const uint8_t *data, size_t length) {
  uint8_t p[12];
  if (length > 11)
    return false;
  p[0] = reg;
  memcpy(p + 1, data, length);
  return servo.start(id, 3, p, length + 1, 0, millis());
}
void servoPoll(uint32_t now) {
  servo.poll(now);
  if (!servo.done)
    return;
  servo.done = false;
  if (!servo.success) {
    char s[80];
    snprintf(s, sizeof(s), "ERR servo_transaction id=%u status=%u", servo.id,
             servo.error);
    sendLine(s);
    fault("servo_failure");
    return;
  }
  if (servoStage == 1) {
    uint16_t pos = servo.data[0] | (uint16_t(servo.data[1]) << 8);
    if (pos > 4095) {
      fault("servo_position_range");
      return;
    }
    uint8_t p[] = {10, uint8_t(pos), uint8_t(pos >> 8), 0, 0, 100, 0};
    servoStage = 2;
    if (!servoWrite(servoId, 41, p, 7))
      fault("servo_tx_failed");
    return;
  }
  if (servoStage == 2) {
    uint8_t one = 1;
    servoStage = 3;
    if (!servoWrite(servoId, 40, &one, 1))
      fault("servo_tx_failed");
    return;
  }
  servoStage = 0;
  char s[160];
  int used = snprintf(
      s, sizeof(s),
      "{\"servo_id\":%u,\"transmitted\":true,\"acknowledged\":%s,\"data\":[",
      servo.id, servo.acknowledged ? "true" : "false");
  for (size_t j = 0; j < servo.length; j++)
    used += snprintf(s + used, sizeof(s) - used, "%s%u", j ? "," : "",
                     servo.data[j]);
  snprintf(s + used, sizeof(s) - used, "]}");
  sendLine(s);
}
void command(char *line) {
  char *a[32];
  int n = 0;
  char *save = nullptr;
  for (char *t = strtok_r(line, " \t", &save); t;
       t = strtok_r(nullptr, " \t", &save)) {
    if (n == 32) {
      fault("invalid_command");
      sendLine("ERR invalid");
      return;
    }
    a[n++] = t;
  }
  if (!n)
    return;
  uint32_t now = millis();
  applySafety(now);
  long x = 0, y = 0, z = 0, w = 0;
  bool ok = false;
  if (n == 1 && !strcmp(a[0], "status")) {
    telemetry();
    return;
  }
  if (n == 1 && !strcmp(a[0], "stop")) {
    fault("stop");
    sendLine("OK stopped");
    return;
  }
  if (n == 1 && !strcmp(a[0], "zero") && !safety.active()) {
    portENTER_CRITICAL(&encoderMux);
    ticksL = 0;
    ticksR = 0;
    badL = 0;
    badR = 0;
    portEXIT_CRITICAL(&encoderMux);
    sendLine("OK zero");
    return;
  }
  if (n == 2 && !strcmp(a[0], "arm")) {
    char *end = nullptr;
    errno = 0;
    unsigned long token = strtoul(a[1], &end, 10);
    ok = *a[1] && a[1][0] != '-' && !errno && !*end && token <= UINT32_MAX &&
         safety.arm(uint32_t(token), now, inputs());
    sendLine(ok ? "OK arming" : "ERR arm_token_or_conditions");
    return;
  }
  if (n == 1 && !strcmp(a[0], "keepalive")) {
    sendLine(safety.keepalive(now) ? "OK" : "ERR not_armed");
    return;
  }
  if (n == 3 && !strcmp(a[0], "drive") && num(a[1], -100, 100, x) &&
      num(a[2], -100, 100, y)) {
    ok = safety.drive(int(x), int(y), now);
    if (!ok)
      fault("drive_not_armed");
    sendLine(ok ? "OK" : "ERR not_armed");
    return;
  }
  if (n == 3 && !strcmp(a[0], "ramp") && num(a[1], 1, 500, x) &&
      num(a[2], 1, 500, y)) {
    safety.rampUp = x;
    safety.rampDown = y;
    sendLine("OK");
    return;
  }
  if (n == 4 && !strcmp(a[0], "tone") && num(a[1], 100, 4000, x) &&
      num(a[2], 1, 2000, y) && num(a[3], 1, 10, z) && audioOK && inputs().usb &&
      !inputs().usbFault && !inputs().estop) {
    toneHz = x;
    toneMs = y;
    toneAmplitude = 32767 * z / 100;
    tonePhase = 0;
    toneAt = now;
    toneActive = true;
    digitalWrite(pins::AUDIO_ENABLE, HIGH);
    sendLine("OK tone");
    return;
  }
  if (n >= 3 && !strcmp(a[0], "servo") && num(a[2], 1, 253, x)) {
    if (!safety.armed()) {
      sendLine("ERR not_armed");
      return;
    }
    if (servo.busy || servo.done) {
      sendLine("ERR servo_busy");
      return;
    }
    uint8_t id = uint8_t(x);
    servoStage = 0;
    if (!strcmp(a[1], "syncmove") && n >= 10 && (n - 2) % 4 == 0 &&
        (n - 2) / 4 <= 7) {
      feetech::Goal goals[7];
      size_t count = (n - 2) / 4;
      bool valid = true;
      for (size_t j = 0; j < count; j++) {
        long sid, pos, speed, acc;
        int at = 2 + j * 4;
        if (!num(a[at], 1, 253, sid) || !num(a[at + 1], 0, 4095, pos) ||
            !num(a[at + 2], 1, 1500, speed) || !num(a[at + 3], 1, 254, acc)) {
          valid = false;
          break;
        }
        goals[j] = {uint8_t(sid), uint16_t(pos), uint16_t(speed), uint8_t(acc)};
      }
      uint8_t params[58];
      size_t len = valid ? feetech::syncArgs(goals, count, params) : 0;
      if (len)
        ok = servo.start(254, 0x83, params, len, 255, now);
    } else if (n == 3 && !strcmp(a[1], "ping"))
      ok = servo.start(id, 1, nullptr, 0, 0, now);
    else if (n == 5 && !strcmp(a[1], "read") && num(a[3], 0, 70, y) &&
             num(a[4], 1, 8, z) && y + z <= 71)
      ok = servoRead(id, y, z);
    else if (n == 5 && !strcmp(a[1], "write") && num(a[3], 0, 255, y) &&
             num(a[4], 0, 65535, z)) {
      uint8_t len = 0, p[] = {uint8_t(z), uint8_t(z >> 8)};
      if (feetech::allowedWrite(y, z, len))
        ok = servoWrite(id, y, p, len);
    } else if (n == 4 && !strcmp(a[1], "torque") && num(a[3], 0, 1, y)) {
      if (!y) {
        uint8_t zero = 0;
        ok = servoWrite(id, 40, &zero, 1);
      } else {
        servoId = id;
        servoStage = 1;
        ok = servoRead(id, 56, 2);
      }
    } else if (n == 6 && !strcmp(a[1], "move") && num(a[3], 0, 4095, y) &&
               num(a[4], 1, 1500, z) && num(a[5], 1, 254, w)) {
      uint8_t p[] = {uint8_t(w), uint8_t(y), uint8_t(y >> 8), 0,
                     0,          uint8_t(z), uint8_t(z >> 8)};
      ok = servoWrite(id, 41, p, 7);
    }
    if (ok) {
      safety.keepalive(now);
      sendLine("OK servo_pending");
    } else {
      fault("servo_rejected");
      sendLine("ERR servo_invalid_or_tx");
    }
    return;
  }
  fault("invalid_command");
  sendLine("ERR invalid_command");
}
void serviceRx(uint32_t now) {
  if (rx.timedOut(now)) {
    fault("partial_line_timeout");
    return;
  }
  if (rxPurge) {
    for (int j = 0; j < 64 && Serial.available(); j++)
      Serial.read();
    if (!Serial.available())
      rxPurge = false;
    return;
  }
  for (int j = 0; j < 64 && Serial.available(); j++) {
    int result = rx.push(char(Serial.read()), now);
    if (result < 0) {
      fault("serial_invalid");
      return;
    }
    if (result > 0) {
      uint32_t generation = safety.generation;
      command(rx.data);
      if (generation != safety.generation)
        return;
    }
  }
}
void setup() {
  for (int pin :
       {pins::PWM_L, pins::PWM_R, pins::DIR_L, pins::DIR_R, pins::DRIVE_ENABLE,
        pins::SERVO_TX_ENABLE, pins::ACT_POWER_ENABLE, pins::WD_ENABLE,
        pins::WD_TICK, pins::ARM_COMMIT, pins::ENC_POWER_EN, pins::AUDIO_ENABLE,
        pins::STATUS_LED}) {
    digitalWrite(pin, LOW);
    pinMode(pin, OUTPUT);
  }
  for (int pin : {pins::ESTOP_ACTIVE, pins::USB_PWR_FAULT_N, pins::ACT_READY,
                  pins::ARM_LATCHED, pins::DRIVE_RUN, pins::ENC_L_A,
                  pins::ENC_L_B, pins::ENC_R_A, pins::ENC_R_B})
    pinMode(pin, INPUT);
  // The hardware power budget assumes RF off. No Wi-Fi/BLE start or
  // provisioning code.
  esp_wifi_stop();
  esp_bt_controller_disable();
  USB.usbPower(500);
  Serial.setRxBufferSize(512);
  Serial.setTxTimeoutMs(0);
  Serial.enableReboot(false);
  Serial.onEvent(
      ARDUINO_USB_CDC_RX_OVERFLOW_EVENT,
      [](void *, esp_event_base_t, int32_t, void *) { usbOverflow = true; });
  Serial.begin(115200);
  USB.begin();
  pwmOK = ledcAttach(pins::PWM_L, 20000, 10);
  bool rightOK = ledcAttach(pins::PWM_R, 20000, 10);
  pwmOK = pwmOK && rightOK;
  if (!pwmOK) {
    ledcDetach(pins::PWM_L);
    ledcDetach(pins::PWM_R);
    pinMode(pins::PWM_L, OUTPUT);
    pinMode(pins::PWM_R, OUTPUT);
  }
  zeroOutputs();
  Wire.begin(pins::I2C_SDA, pins::I2C_SCL, 100000);
  Wire.setTimeOut(5);
  servo.begin();
  audioOK = audioInit();
  prevL = (digitalRead(pins::ENC_L_A) << 1) | digitalRead(pins::ENC_L_B);
  prevR = (digitalRead(pins::ENC_R_A) << 1) | digitalRead(pins::ENC_R_B);
  attachInterrupt(pins::ENC_L_A, encoderLeft, CHANGE);
  attachInterrupt(pins::ENC_L_B, encoderLeft, CHANGE);
  attachInterrupt(pins::ENC_R_A, encoderRight, CHANGE);
  attachInterrupt(pins::ENC_R_B, encoderRight, CHANGE);
  safety.token = esp_random();
  if (!safety.token)
    safety.token = 1;
  // WDI high BEFORE SET1; first falling edge >=1ms later, well beyond the 150us
  // setup.
  digitalWrite(pins::WD_TICK, HIGH);
  digitalWrite(pins::WD_ENABLE, HIGH);
  watchdog.start(micros());
  lastLoopUs = micros();
}
void loop() {
  uint32_t us = micros(), now = millis();
  uint32_t gap = us - lastLoopUs;
  lastLoopUs = us;
  if (gap > maxLoopUs)
    maxLoopUs = gap;
  // Never feed the external watchdog independently of this complete bounded
  // control iteration.
  if (gap >= 100000 && safety.active())
    fault("loop_late");
  bool open = usbOpen();
  if (usbWasOpen && !open)
    fault("usb_disconnected");
  usbWasOpen = open;
  if (usbOverflow) {
    usbOverflow = false;
    fault("usb_rx_overflow");
  }
  if (open != encoderPower) {
    encoderPower = open;
    encoderPowerAt = now;
    encodersReady = false;
    digitalWrite(pins::ENC_POWER_EN, open);
  }
  if (open && !encodersReady && uint32_t(now - encoderPowerAt) >= 30) {
    portENTER_CRITICAL(&encoderMux);
    prevL = (digitalRead(pins::ENC_L_A) << 1) | digitalRead(pins::ENC_L_B);
    prevR = (digitalRead(pins::ENC_R_A) << 1) | digitalRead(pins::ENC_R_B);
    encodersReady = true;
    portEXIT_CRITICAL(&encoderMux);
  }
  applySafety(now);
  serviceRx(now);
  applySafety(millis());
  if (safety.armed())
    servoPoll(millis());
  else if (servo.busy)
    servo.abort();
  static bool senseTurn = false;
  senseTurn = !senseTurn;
  if (senseTurn)
    sensors.inaStep(i2c, millis());
  else
    sensors.adsStep(i2c, millis());
  applySafety(millis());
  audioPoll(millis());
  if (uint32_t(now - lastTelemetry) >= 200) {
    lastTelemetry = now;
    telemetry();
  }
  serviceTx();
  digitalWrite(pins::STATUS_LED,
               safety.armed() ? HIGH
                              : ((now / (safety.faulted() ? 125 : 500)) % 2));
  if (watchdog.poll(micros()))
    digitalWrite(pins::WD_TICK, watchdog.high);
  delay(1);
}
