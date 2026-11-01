// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "Feetech.h"
#include "Pins.h"
#include <Arduino.h>
#include <driver/uart.h>
// UART1, 1 Mbaud, 8N1. A single request is outstanding; TX has no software
// queue.
struct ServoBus {
  bool initialized = false, busy = false, txActive = false, done = false,
       success = false, acknowledged = false;
  uint8_t id = 0, expected = 0, error = 0, data[8]{};
  size_t length = 0, txLength = 0;
  uint8_t tx[feetech::CAP]{};
  uint32_t began = 0;
  feetech::Parser parser;
  bool begin() {
    uart_config_t c{};
    c.baud_rate = 1000000;
    c.data_bits = UART_DATA_8_BITS;
    c.parity = UART_PARITY_DISABLE;
    c.stop_bits = UART_STOP_BITS_1;
    c.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    c.source_clk = UART_SCLK_DEFAULT;
    initialized =
        uart_param_config(UART_NUM_1, &c) == ESP_OK &&
        uart_set_pin(UART_NUM_1, pins::SERVO_TX, pins::SERVO_RX,
                     UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE) == ESP_OK &&
        uart_driver_install(UART_NUM_1, 256, 0, 0, nullptr, 0) == ESP_OK;
    return initialized;
  }
  void abort() {
    digitalWrite(pins::SERVO_TX_ENABLE, LOW);
    busy = txActive = done = false;
    parser.reset();
    if (initialized)
      uart_flush_input(UART_NUM_1);
  }
  bool start(uint8_t sid, uint8_t op, const uint8_t *p, size_t n,
             uint8_t responseBytes, uint32_t now) {
    if (!initialized || busy)
      return false;
    // A previous aborted FIFO must be completely idle before reopening the
    // physical gate.
    if (uart_wait_tx_done(UART_NUM_1, 0) != ESP_OK)
      return false;
    txLength = feetech::packet(sid, op, p, n, tx);
    if (!txLength || txLength > 64)
      return false;
    uart_flush_input(UART_NUM_1);
    parser.reset();
    done = success = false;
    length = error = 0;
    id = sid;
    expected = responseBytes;
    digitalWrite(pins::SERVO_TX_ENABLE, HIGH);
    int written =
        uart_tx_chars(UART_NUM_1, reinterpret_cast<const char *>(tx), txLength);
    if (written != int(txLength)) {
      digitalWrite(pins::SERVO_TX_ENABLE, LOW);
      return false;
    }
    // One <=64-byte command at 1Mbaud is <=640us on wire. Release OE at actual
    // TX_DONE, not at the next 1ms loop (a servo may answer sooner). No
    // yield/flush with unbounded wait.
    uint32_t startedUs = micros();
    while (uart_wait_tx_done(UART_NUM_1, 0) != ESP_OK) {
      if (uint32_t(micros() - startedUs) >= 1500) {
        digitalWrite(pins::SERVO_TX_ENABLE, LOW);
        return false;
      }
    }
    digitalWrite(pins::SERVO_TX_ENABLE, LOW);
    began = now;
    busy = true;
    txActive = false;
    acknowledged = false;
    if (responseBytes == 255) {
      busy = false;
      done = true;
      success = true;
    }
    return true;
  }
  void finish(bool ok) {
    digitalWrite(pins::SERVO_TX_ENABLE, LOW);
    txActive = busy = false;
    success = ok;
    done = true;
  }
  void poll(uint32_t now) {
    if (!busy)
      return;
    if (uint32_t(now - began) >= 20) {
      finish(false);
      return;
    }
    if (txActive) {
      if (uart_wait_tx_done(UART_NUM_1, 0) != ESP_OK)
        return;
      digitalWrite(pins::SERVO_TX_ENABLE, LOW);
      txActive = false;
    }
    for (unsigned budget = 0; budget < 64; budget++) {
      uint8_t b;
      if (uart_read_bytes(UART_NUM_1, &b, 1, 0) != 1)
        break;
      if (!parser.push(b))
        continue;
      bool echo =
          parser.used == txLength && !memcmp(parser.bytes, tx, txLength);
      if (!echo && parser.bytes[2] == id) {
        error = parser.bytes[4];
        length = parser.bytes[3] - 2;
        if (length <= sizeof(data))
          memcpy(data, parser.bytes + 5, length);
        acknowledged = true;
        finish(error == 0 && length == expected);
        parser.reset();
        return;
      }
      parser.reset();
    }
  }
};
