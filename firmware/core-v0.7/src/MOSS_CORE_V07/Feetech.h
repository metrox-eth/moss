// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>
namespace feetech {
constexpr size_t CAP = 80;
inline size_t packet(uint8_t id, uint8_t op, const uint8_t *args, size_t n,
                     uint8_t *out) {
  if (id < 1 || (id > 253 && !(id == 254 && op == 0x83)) || n > CAP - 6)
    return 0;
  out[0] = out[1] = 255;
  out[2] = id;
  out[3] = uint8_t(n + 2);
  out[4] = op;
  uint8_t sum = id + out[3] + op;
  for (size_t j = 0; j < n; j++) {
    out[5 + j] = args[j];
    sum += args[j];
  }
  out[5 + n] = uint8_t(~sum);
  return n + 6;
}
struct Parser {
  uint8_t bytes[CAP]{};
  size_t used = 0;
  void reset() { used = 0; }
  // Fully validated packet only. Caller must reset after inspecting a complete
  // packet.
  bool push(uint8_t b) {
    if (used < 2) {
      if (b == 255)
        bytes[used++] = b;
      else
        used = 0;
      return false;
    }
    if (used == 2 && b == 255)
      return false;
    bytes[used++] = b;
    if (used == 4 && (bytes[3] < 2 || bytes[3] > CAP - 4)) {
      reset();
      return false;
    }
    if (used >= 6 && used == size_t(bytes[3]) + 4) {
      uint8_t sum = 0;
      for (size_t j = 2; j < used; j++)
        sum += bytes[j];
      if (sum == 255)
        return true;
      reset();
    }
    return false;
  }
};
inline bool allowedWrite(uint8_t reg, uint16_t value, uint8_t &size) {
  // Deliberately narrow SRAM-only raw writes; torque-on and goals use guarded
  // commands.
  if (reg == 40 && value == 0) {
    size = 1;
    return true;
  }
  if (reg == 41 && value >= 1 && value <= 254) {
    size = 1;
    return true;
  }
  if (reg == 46 && value >= 1 && value <= 1500) {
    size = 2;
    return true;
  }
  return false;
}
struct Goal {
  uint8_t id;
  uint16_t position, speed;
  uint8_t acceleration;
};
inline size_t syncArgs(const Goal *goals, size_t count, uint8_t *args) {
  if (count < 2 || count > 7)
    return 0;
  args[0] = 41;
  args[1] = 7;
  for (size_t j = 0; j < count; j++) {
    const Goal &g = goals[j];
    if (g.id < 1 || g.id > 253 || g.position > 4095 || g.speed < 1 ||
        g.speed > 1500 || g.acceleration < 1 || g.acceleration > 254)
      return 0;
    for (size_t k = 0; k < j; k++)
      if (goals[k].id == g.id)
        return 0;
    size_t at = 2 + j * 8;
    args[at] = g.id;
    args[at + 1] = g.acceleration;
    args[at + 2] = uint8_t(g.position);
    args[at + 3] = uint8_t(g.position >> 8);
    args[at + 4] = args[at + 5] = 0;
    args[at + 6] = uint8_t(g.speed);
    args[at + 7] = uint8_t(g.speed >> 8);
  }
  return 2 + count * 8;
}
} // namespace feetech
