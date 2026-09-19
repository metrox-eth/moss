#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

namespace moss {
constexpr int MAX_PERCENT = 25;  // Commissioning limit; raise only after mechanical tests.
constexpr uint32_t COMMAND_TIMEOUT_MS = 300;
constexpr uint32_t ARM_TIMEOUT_MS = 10000;
constexpr uint32_t TEST_MS = 1000;

enum Mode { OFF, READY, DRIVE, TEST };
enum Reply { OK, STATUS, ZERO, INVALID, NOT_ARMED, BUSY };

struct Control {
  Mode mode = OFF;
  int left = 0, right = 0;
  uint32_t since = 0;
  const char* reason = "boot";
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
  static bool number(const char* s, int& out) {
    if (!s || !*s) return false;
    errno = 0; char* end;
    long n = strtol(s, &end, 10);
    if (errno || *end || n < -MAX_PERCENT || n > MAX_PERCENT) return false;
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
    if (argc == 3 && !strcmp(argv[0], "drive") && number(argv[1], l) && number(argv[2], r)) {
      if (mode != READY && mode != DRIVE) { stop("not_armed"); return NOT_ARMED; }
      left = l; right = r; mode = DRIVE; since = now; reason = "drive"; return OK;
    }
    if (argc == 3 && !strcmp(argv[0], "test") && number(argv[2], l) &&
        (!strcmp(argv[1], "left") || !strcmp(argv[1], "right"))) {
      if (mode != OFF) { stop("test_requires_stop"); return BUSY; }
      left = !strcmp(argv[1], "left") ? l : 0;
      right = !strcmp(argv[1], "right") ? l : 0;
      mode = TEST; since = now; reason = "test"; return OK;
    }
    stop("invalid"); return INVALID;
  }
};

// Sign changes first ramp to zero, then wait before changing DIR.
struct Ramp {
  int value = 0;
  int sign = 1;
  uint32_t zeroSince = 0;
  void stop(uint32_t now) { value = 0; zeroSince = now; }
  int tick(int target, uint32_t now) {
    if (!target) { if (value) stop(now); return 0; }
    int desiredSign = target < 0 ? -1 : target > 0 ? 1 : sign;
    int magnitude = target < 0 ? -target : target;
    if (desiredSign != sign) {
      if (value > 0) {
        --value;
        if (!value) zeroSince = now;
        return sign * value;
      }
      if (uint32_t(now - zeroSince) < 100) return 0;
      sign = desiredSign;
    }
    if (value < magnitude) ++value;
    else if (value > magnitude) { --value; if (!value) zeroSince = now; }
    return sign * value;
  }
};
}
