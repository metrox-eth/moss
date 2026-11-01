// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "Core.h"
namespace core07 {
// Bus implements read(address,register,uint16_t&) and
// write(address,register,uint16_t). Exactly one register operation per step,
// including recovery. No invented calibration/protection threshold.
struct Sensors {
  Sample battery, analog[4];
  uint32_t errors = 0;
  int inaPhase = 0, adsPhase = 0;
  uint8_t channel = 0;
  uint32_t inaAt = 0, adsAt = 0;
  bool inaDelay = false, adsDelay = false;
  static constexpr uint16_t INA_CONFIG =
      0x4126; // 1 sample, 1.1ms, bus-only continuous
  uint16_t adsConfig() const {
    return uint16_t(0x8000u | ((4u + channel) << 12) | 0x0200u | 0x0100u |
                    0x00e0u | 3u);
  }
  void failIna(uint32_t t) {
    battery.valid = false;
    inaPhase = 0;
    inaAt = t;
    inaDelay = true;
    errors++;
  }
  void failAds(uint32_t t) {
    for (auto &v : analog)
      v.valid = false;
    adsPhase = 0;
    adsAt = t;
    adsDelay = true;
    errors++;
  }
  template <class Bus> void inaStep(Bus &b, uint32_t t) {
    if (inaDelay) {
      if (uint32_t(t - inaAt) < 1000)
        return;
      inaDelay = false;
    }
    uint16_t v = 0;
    bool ok = true;
    switch (inaPhase) {
    case 0:
      ok = b.read(0x40, 0xfe, v) && v == 0x5449;
      break;
    case 1:
      ok = b.read(0x40, 0xff, v) && (v & 0xfff0) == 0x2260;
      break;
    case 2:
      ok = b.write(0x40, 0, INA_CONFIG);
      break;
    case 3:
      ok = b.read(0x40, 0, v) && v == INA_CONFIG;
      break;
    case 4:
      if (uint32_t(t - inaAt) < 100)
        return;
      ok = b.read(0x40, 6, v);
      if (ok && !(v & 8)) {
        if (uint32_t(t - inaAt) > 500)
          failIna(t);
        return;
      }
      break;
    case 5:
      ok = b.read(0x40, 2, v) && !(v & 0x8000);
      if (ok) {
        battery.set(v * 0.00125f, t);
        inaAt = t;
        inaPhase = 3;
        return;
      }
      break;
    }
    if (!ok) {
      failIna(t);
      return;
    }
    ++inaPhase;
  }
  template <class Bus> void adsStep(Bus &b, uint32_t t) {
    if (adsDelay) {
      if (uint32_t(t - adsAt) < 1000)
        return;
      adsDelay = false;
    }
    uint16_t v = 0;
    bool ok = true;
    if (adsPhase == 0) {
      ok = b.write(0x48, 1, adsConfig());
      adsAt = t;
      if (ok)
        adsPhase = 1;
    } else if (adsPhase == 1) {
      if (uint32_t(t - adsAt) < 2)
        return;
      ok = b.read(0x48, 1, v) && (v & 0x7fff) == (adsConfig() & 0x7fff);
      if (ok && (v & 0x8000))
        adsPhase = 2;
      else if (ok && uint32_t(t - adsAt) >= 20)
        ok = false;
    } else {
      float volts = 0;
      ok = b.read(0x48, 0, v) &&
           (channel == 3 ? (int16_t(v) != -32768 && int16_t(v) != 32767)
                         : adcVoltage(int16_t(v), volts));
      if (ok && channel == 3)
        volts = int16_t(v) * 0.000125f;
      if (ok && channel == 2 && (volts < 3.0f || volts > 3.6f))
        ok = false;
      if (ok) {
        analog[channel].set(volts, t);
        channel = (channel + 1) % 4;
        adsPhase = 0;
      }
    }
    if (!ok)
      failAds(t);
  }
};
} // namespace core07
