// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "LegacyControl.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
namespace core07 {
constexpr uint32_t LEASE_MS = 300, READY_STABLE_MS = 10, MARGIN_MS = 2,
                   POWER_TIMEOUT_MS = 1000;
enum class State {
  Off,
  WaitReady,
  ClearMargin,
  CommitHigh,
  CommitLow,
  Armed,
  Driving
};
struct Inputs {
  bool usb = false, estop = false, usbFault = false, ready = false,
       latch = false, driveRun = false, pwmOK = true;
};
struct Safety {
  State state = State::Off;
  const char *reason = "boot";
  uint32_t token = 1, generation = 0, began = 0, phase = 0, lastHost = 0,
           lastDrive = 0, stableAt = 0;
  bool stable = false;
  int left = 0, right = 0;
  uint32_t rampUp = 30, rampDown = 15;
  bool active() const { return state != State::Off; }
  bool faulted() const {
    return state == State::Off && strcmp(reason, "boot") &&
           strcmp(reason, "stop");
  }
  bool armed() const {
    return state == State::Armed || state == State::Driving;
  }
  bool power() const { return active(); }
  bool commit() const { return state == State::CommitHigh; }
  bool driveEnable() const { return state == State::Driving; }
  void stop(const char *why) {
    state = State::Off;
    left = right = 0;
    stable = false;
    reason = why;
    ++generation;
    token = token * 1664525u + 1013904223u;
    if (!token)
      token = 1;
  }
  bool healthy(const Inputs &i) const {
    return i.usb && !i.estop && !i.usbFault && i.pwmOK;
  }
  bool arm(uint32_t key, uint32_t now, const Inputs &i) {
    if (active() || key != token || !healthy(i) || i.latch || i.driveRun)
      return false;
    ++token;
    if (!token)
      token = 1;
    state = State::WaitReady;
    reason = "power_wait";
    began = phase = lastHost = now;
    stable = false;
    left = right = 0;
    return true;
  }
  bool keepalive(uint32_t now) {
    if (!active())
      return false;
    lastHost = now;
    return true;
  }
  bool drive(int l, int r, uint32_t now) {
    if (!armed() || l < -100 || l > 100 || r < -100 || r > 100)
      return false;
    left = l;
    right = r;
    state = State::Driving;
    reason = "drive";
    lastDrive = lastHost = now;
    return true;
  }
  void poll(uint32_t now, const Inputs &i) {
    if (!active())
      return;
    if (!healthy(i)) {
      stop(!i.usb       ? "usb_disconnected"
           : i.estop    ? "estop"
           : i.usbFault ? "usb_power_fault"
                        : "pwm_init_failed");
      return;
    }
    if (uint32_t(now - lastHost) >= LEASE_MS) {
      stop("usb_timeout");
      return;
    }
    if (state == State::Driving && uint32_t(now - lastDrive) >= LEASE_MS) {
      stop("drive_timeout");
      return;
    }
    if (armed()) {
      if (!i.ready)
        stop("act_ready_lost");
      else if (!i.latch)
        stop("arm_latch_lost");
      return;
    }
    if (uint32_t(now - began) >= POWER_TIMEOUT_MS) {
      stop("arm_timeout");
      return;
    }
    if (state == State::WaitReady) {
      if (i.latch) {
        stop("latch_not_clear");
        return;
      }
      if (!i.ready) {
        stable = false;
        return;
      }
      if (!stable) {
        stable = true;
        stableAt = now;
      }
      if (uint32_t(now - stableAt) >= READY_STABLE_MS) {
        state = State::ClearMargin;
        phase = now;
      }
      return;
    }
    if (!i.ready) {
      stop("ready_during_arm");
      return;
    }
    if (state == State::ClearMargin && i.latch) {
      stop("unexpected_latch");
      return;
    }
    if (uint32_t(now - phase) < MARGIN_MS)
      return;
    if (state == State::ClearMargin) {
      state = State::CommitHigh;
      phase = now;
    } else if (state == State::CommitHigh) {
      state = State::CommitLow;
      phase = now;
    } else if (state == State::CommitLow) {
      if (!i.latch)
        stop("latch_failed");
      else {
        state = State::Armed;
        reason = "armed";
      }
    }
  }
};
// Bounded line parsing shared by native USB and host tests. No partial line
// survives a fault.
struct Lines {
  char data[256]{};
  size_t used = 0;
  uint32_t began = 0;
  bool discard = false;
  void reset() {
    used = 0;
    discard = false;
  }
  bool timedOut(uint32_t now) {
    if (used && uint32_t(now - began) >= 100) {
      used = 0;
      discard = true;
      return true;
    }
    return false;
  }
  // 1 complete, 0 incomplete, -1 malformed. Caller consumes data before next
  // push.
  int push(char c, uint32_t now) {
    if (c == '\r')
      return 0;
    if (c == '\n') {
      if (discard) {
        reset();
        return 0;
      }
      data[used] = 0;
      bool valid = used > 0;
      used = 0;
      return valid ? 1 : 0;
    }
    if (discard)
      return 0;
    if ((c < 32 && c != '\t') || c > 126 || used == sizeof(data) - 1) {
      used = 0;
      discard = true;
      return -1;
    }
    if (!used)
      began = now;
    data[used++] = c;
    return 0;
  }
};
struct Sample {
  float value = 0;
  uint32_t at = 0;
  bool valid = false;
  void set(float v, uint32_t t) {
    value = v;
    at = t;
    valid = true;
  }
  bool fresh(uint32_t now) const { return valid && uint32_t(now - at) < 500; }
};
inline bool adcVoltage(int16_t raw, float &v) {
  if (raw < 0 || raw == 32767)
    return false;
  v = raw * 0.000125f;
  return true;
}
inline bool current(const Sample &signal, const Sample &rail, uint32_t now,
                    float &amps) {
  if (!signal.fresh(now) || !rail.fresh(now) ||
      (rail.value < 3.0f || rail.value > 3.6f) || signal.value < 0 ||
      signal.value > rail.value)
    return false;
  amps = (signal.value - rail.value * 0.5f) / 0.1f;
  return true;
}
struct Watchdog {
  uint32_t at = 0;
  bool enabled = false, high = true, first = true;
  void start(uint32_t us) {
    enabled = true;
    high = true;
    first = true;
    at = us;
  }
  bool poll(uint32_t us) {
    if (!enabled)
      return false;
    uint32_t wait = first ? 1000u : 10000u;
    if (uint32_t(us - at) < wait)
      return false;
    high = !high;
    at = us;
    first = false;
    return true;
  }
};
} // namespace core07
