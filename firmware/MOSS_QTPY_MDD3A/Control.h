#pragma once
// MOSS V0.4 control logic - same protocol as the V0.3 bench firmware (arm /
// drive L R / stop / status / zero / test), plus a configurable ramp:
//   ramp UP DOWN   milliseconds per 1 % of PWM, rise and fall separately
// Defaults below: 0 -> 100 % in 1.0 s, 100 -> 0 in 0.5 s (10/10: the first
// drive on the floor with the arm mounted, Laurent: "100 %", the 25 % bench
// limit and the 30 ms rise never got the tracks moving); tune with "ramp".
// MAX_PERCENT stays a compile-time limit, not a serial command: 100 since
// 10/10 (the commissioning 25 % was the bench on blocks, 05/10); the host
// side caps lower with MOSS_MAX_PCT when it wants to.
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

namespace moss {
constexpr int MAX_PERCENT = 100; // Full PWM = the motors' rated 12 V (bench 05/10 was 25 %, raised 10/10).
constexpr uint32_t COMMAND_TIMEOUT_MS = 300;
constexpr uint32_t ARM_TIMEOUT_MS = 10000;
constexpr uint32_t TEST_MS = 1000;
constexpr uint32_t RAMP_RISE_MS_DEFAULT = 10;   // ms per 1 % up   (0 -> 100 % in 1.0 s)
constexpr uint32_t RAMP_FALL_MS_DEFAULT = 5;    // ms per 1 % down (100 -> 0 % in 0.5 s)
constexpr uint32_t RAMP_MS_MIN = 1, RAMP_MS_MAX = 500;
constexpr uint32_t REVERSE_DWELL_MS = 100;      // at zero before changing direction

enum Mode { OFF, READY, DRIVE, TEST };
enum Reply { OK, STATUS, ZERO, INVALID, NOT_ARMED, BUSY };

struct Control {
  Mode mode = OFF;
  int left = 0, right = 0;
  uint32_t since = 0;
  const char* reason = "boot";
  uint32_t rampRiseMs = RAMP_RISE_MS_DEFAULT, rampFallMs = RAMP_FALL_MS_DEFAULT;
  void stop(const char* why) {
    mode = OFF; left = right = 0; reason = why;
  }
  bool poll(uint32_t now) {
    uint32_t age = now - since;  // Defined across millis() rollover.
    if (mode == DRIVE && age >= COMMAND_TIMEOUT_MS) { stop("timeout"); return true; }
    if (mode == READY && age >= ARM_TIMEOUT_MS) { stop("arm_expired"); return true; }
    if (mode == TEST && age >= TEST_MS) { stop("test_done"); return true; }
    return false;
  }
  static bool number(const char* s, long lo, long hi, long& out) {
    if (!s || !*s) return false;
    errno = 0; char* end;
    long n = strtol(s, &end, 10);
    if (errno || *end || n < lo || n > hi) return false;
    out = n; return true;
  }
  static bool percent(const char* s, int& out) {
    long n; if (!number(s, -MAX_PERCENT, MAX_PERCENT, n)) return false;
    out = static_cast<int>(n); return true;
  }
  Reply command(char* line, uint32_t now) {
    poll(now);
    char* argv[4]; int argc = 0; char* save = nullptr;
    for (char* t = strtok_r(line, " \t", &save); t; t = strtok_r(nullptr, " \t", &save)) {
      if (argc == 4) { stop("invalid"); return INVALID; }
      argv[argc++] = t;
    }
    if (!argc) return OK;
    if (argc == 1 && !strcmp(argv[0], "stop")) { stop("stop"); return OK; }
    if (argc == 1 && !strcmp(argv[0], "status")) return STATUS;
    if (argc == 1 && !strcmp(argv[0], "zero")) {
      if (mode != OFF) { stop("zero_requires_stop"); return BUSY; }
      return ZERO;
    }
    if (argc == 1 && !strcmp(argv[0], "arm")) {
      if (mode == DRIVE || mode == TEST) { stop("arm_while_moving"); return BUSY; }
      mode = READY; left = right = 0; since = now; reason = "armed"; return OK;
    }
    int l, r;
    if (argc == 3 && !strcmp(argv[0], "drive") && percent(argv[1], l) && percent(argv[2], r)) {
      if (mode != READY && mode != DRIVE) { stop("not_armed"); return NOT_ARMED; }
      left = l; right = r; mode = DRIVE; since = now; reason = "drive"; return OK;
    }
    if (argc == 3 && !strcmp(argv[0], "test") && percent(argv[2], l) &&
        (!strcmp(argv[1], "left") || !strcmp(argv[1], "right"))) {
      if (mode != OFF) { stop("test_requires_stop"); return BUSY; }
      left = !strcmp(argv[1], "left") ? l : 0;
      right = !strcmp(argv[1], "right") ? l : 0;
      mode = TEST; since = now; reason = "test"; return OK;
    }
    long up, down;
    if (argc == 3 && !strcmp(argv[0], "ramp") &&
        number(argv[1], RAMP_MS_MIN, RAMP_MS_MAX, up) && number(argv[2], RAMP_MS_MIN, RAMP_MS_MAX, down)) {
      // Allowed while moving: the next ticks simply use the new slopes.
      rampRiseMs = static_cast<uint32_t>(up); rampFallMs = static_cast<uint32_t>(down);
      return OK;
    }
    stop("invalid"); return INVALID;
  }
};

// Output ramp: value moves 1 % per rampRiseMs (towards a larger magnitude) or
// per rampFallMs (towards zero). A sign change first ramps to zero, then waits
// REVERSE_DWELL_MS before the direction bit flips.
struct Ramp {
  int value = 0;          // 0..MAX_PERCENT magnitude currently output
  int sign = 1;
  uint32_t lastStep = 0;
  uint32_t zeroSince = 0;
  void stop(uint32_t now) { value = 0; zeroSince = now; lastStep = now; }
  int tick(int target, uint32_t now, uint32_t riseMs, uint32_t fallMs) {
    if (!target) {
      if (value && uint32_t(now - lastStep) >= fallMs) { --value; lastStep = now; if (!value) zeroSince = now; }
      return sign * value;
    }
    int desiredSign = target < 0 ? -1 : 1;
    int magnitude = target < 0 ? -target : target;
    if (desiredSign != sign) {
      if (value > 0) {
        if (uint32_t(now - lastStep) >= fallMs) { --value; lastStep = now; if (!value) zeroSince = now; }
        return sign * value;
      }
      if (uint32_t(now - zeroSince) < REVERSE_DWELL_MS) return 0;
      sign = desiredSign; lastStep = now;   // the rise slope starts after the dwell, not before
    }
    if (value < magnitude) {
      if (uint32_t(now - lastStep) >= riseMs) { ++value; lastStep = now; }
    } else if (value > magnitude) {
      if (uint32_t(now - lastStep) >= fallMs) { --value; lastStep = now; if (!value) zeroSince = now; }
    }
    return sign * value;
  }
};
}
