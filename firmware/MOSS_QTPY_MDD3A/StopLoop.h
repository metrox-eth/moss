#pragma once
#include <stdint.h>

namespace moss {
// Normally closed contact to ground. An open input trips immediately; closing
// it again only starts the debounce period, never clears the latched stop.
struct StopLoop {
  static constexpr uint32_t CLOSE_STABLE_MS = 100;
  bool sampled = false, open = true, latched = false;
  uint32_t closedSince = 0;

  void trip(uint32_t now) { latched = true; closedSince = now; }
  void sample(bool isOpen, uint32_t now) {
    if (isOpen) trip(now);
    if (!isOpen && (!sampled || open)) closedSince = now;
    open = isOpen;
    sampled = true;
  }
  bool blocked() const { return !sampled || open || latched; }
  bool clear(uint32_t now) {
    if (!sampled || open || uint32_t(now - closedSince) < CLOSE_STABLE_MS) return false;
    latched = false;
    return true;
  }
};
}
