// SPDX-License-Identifier: Apache-2.0
#include "Core.h"
#include "Feetech.h"
#include "Sensors.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
#include <string>
using namespace core07;
static unsigned checks = 0;
#define CHECK(x)                                                               \
  do {                                                                         \
    ++checks;                                                                  \
    if (!(x)) {                                                                \
      fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x);                     \
      abort();                                                                 \
    }                                                                          \
  } while (0)
Inputs good() {
  Inputs i;
  i.usb = true;
  i.pwmOK = true;
  return i;
}
uint32_t armed(Safety &c, Inputs &i, uint32_t t = 100) {
  CHECK(c.arm(c.token, t, i));
  CHECK(c.power());
  CHECK(!c.commit());
  CHECK(!c.driveEnable());
  c.poll(t + 1, i);
  CHECK(c.state == State::WaitReady);
  i.ready = true;
  c.poll(t + 2, i);
  c.poll(t + 11, i);
  CHECK(c.state == State::WaitReady);
  c.poll(t + 12, i);
  CHECK(c.state == State::ClearMargin);
  c.poll(t + 13, i);
  CHECK(!c.commit());
  c.poll(t + 14, i);
  CHECK(c.commit());
  i.latch = true;
  c.poll(t + 16, i);
  CHECK(c.state == State::CommitLow);
  c.poll(t + 18, i);
  CHECK(c.armed());
  CHECK(!c.driveEnable());
  return t + 18;
}
struct FakeBus {
  bool fail = false, busy = false, wrongConfig = false;
  uint16_t adc = 13536;
  int writes = 0, reads = 0;
  uint16_t cfg = 0;
  bool read(uint8_t addr, uint8_t reg, uint16_t &v) {
    reads++;
    if (fail)
      return false;
    if (addr == 0x40) {
      switch (reg) {
      case 0xfe:
        v = 0x5449;
        break;
      case 0xff:
        v = 0x2261;
        break;
      case 0:
        v = wrongConfig ? 0x4127 : 0x4126;
        break;
      case 6:
        v = busy ? 0 : 8;
        break;
      case 2:
        v = 9600;
        break;
      default:
        return false;
      }
    } else if (addr == 0x48) {
      if (reg == 1)
        v = (cfg & 0x7fff) | (busy ? 0 : 0x8000);
      else if (reg == 0)
        v = ((cfg >> 12) & 7) == 6   ? 27072
            : ((cfg >> 12) & 7) == 7 ? uint16_t(-2)
                                     : adc;
      else
        return false;
    } else
      return false;
    return true;
  }
  bool write(uint8_t addr, uint8_t, uint16_t v) {
    writes++;
    if (fail)
      return false;
    if (addr == 0x48)
      cfg = v;
    return true;
  }
};
int main() {
  {
    Safety s;
    CHECK(!s.active());
    CHECK(!s.faulted());
    s.stop("stop");
    CHECK(!s.faulted());
    s.stop("invalid");
    CHECK(s.faulted());
    s.stop("stop");
    CHECK(!s.power());
    CHECK(!s.commit());
    CHECK(!s.drive(20, 20, 0));
    CHECK(s.left == 0);
    Inputs i = good();
    auto old = s.token;
    auto t = armed(s, i);
    CHECK(!s.arm(old, t, i));
    CHECK(s.drive(50, -50, t));
    CHECK(s.driveEnable());
    CHECK(s.left == 50);
    i.ready = false;
    s.poll(t + 1, i);
    CHECK(!s.active());
    CHECK(s.left == 0 && s.right == 0);
    i.ready = true;
    i.latch = false;
    s.poll(t + 2, i);
    CHECK(!s.active());
    CHECK(!s.arm(old, t + 2, i));
    CHECK(s.arm(s.token, t + 2, i));
  }
  for (int fault = 0; fault < 5; fault++) {
    Safety s;
    Inputs i = good();
    auto t = armed(s, i);
    s.drive(30, 20, t);
    switch (fault) {
    case 0:
      i.usb = false;
      break;
    case 1:
      i.estop = true;
      break;
    case 2:
      i.usbFault = true;
      break;
    case 3:
      i.latch = false;
      break;
    case 4:
      i.pwmOK = false;
      break;
    }
    s.poll(t + 1, i);
    CHECK(!s.active());
    CHECK(s.left == 0);
    CHECK(!s.commit());
  }
  {
    Safety s;
    Inputs i = good();
    uint32_t t = armed(s, i, UINT32_MAX - 120);
    s.drive(100, 100, t);
    s.keepalive(t + 200);
    s.poll(t + 299, i);
    CHECK(s.active());
    s.poll(t + 300, i);
    CHECK(!s.active());
    CHECK(!strcmp(s.reason, "drive_timeout"));
  }
  {
    Safety s;
    Inputs i = good();
    uint32_t t = armed(s, i);
    s.poll(t + 299 - 18, i);
    CHECK(s.active());
    s.poll(t + 300 - 18, i);
    CHECK(!s.active());
  }
  {
    Safety s;
    Inputs i = good();
    s.arm(s.token, 0, i);
    for (uint32_t t = 200; t <= 1000; t += 200) {
      s.keepalive(t);
      s.poll(t, i);
    }
    CHECK(!s.active());
    CHECK(!strcmp(s.reason, "arm_timeout"));
  }
  {
    Safety s;
    Inputs i = good();
    i.latch = true;
    CHECK(!s.arm(s.token, 0, i));
    i.latch = false;
    CHECK(s.arm(s.token, 1, i));
    i.ready = true;
    s.poll(2, i);
    s.poll(12, i);
    i.ready = false;
    s.poll(13, i);
    CHECK(!s.active());
  }
  {
    Safety s;
    Inputs i = good();
    CHECK(s.arm(s.token, 0, i));
    i.ready = true;
    s.poll(1, i);
    s.poll(11, i);
    s.poll(13, i);
    s.poll(15, i);
    s.poll(17, i);
    CHECK(!s.active());
    CHECK(!strcmp(s.reason, "latch_failed"));
  }
  {
    Safety s;
    Inputs i = good();
    CHECK(s.arm(s.token, 0, i));
    i.ready = true;
    s.poll(1, i);
    i.ready = false;
    s.poll(9, i);
    i.ready = true;
    s.poll(10, i);
    s.poll(19, i);
    CHECK(s.state == State::WaitReady);
    s.poll(20, i);
    CHECK(s.state == State::ClearMargin);
  }
  {
    Lines l;
    for (char c : std::string("drive 10 20"))
      CHECK(l.push(c, UINT32_MAX - 50) == 0);
    CHECK(!l.timedOut(48));
    CHECK(l.timedOut(49));
    CHECK(l.push('\n', 50) == 0);
    for (int j = 0; j < 255; j++)
      CHECK(l.push('x', 100) == 0);
    CHECK(l.push('x', 100) == -1);
    CHECK(l.push('\n', 100) == 0);
    CHECK(l.push('\1', 100) == -1);
    l.reset();
    CHECK(l.push('a', 100) == 0);
    CHECK(l.push('\n', 100) == 1);
    CHECK(!strcmp(l.data, "a"));
  }
  {
    Safety s;
    Inputs i = good();
    uint32_t old = s.token;
    s.stop("fault");
    CHECK(!s.arm(old, 20, i));
    CHECK(!s.drive(100, 100, 20));
    Lines l;
    for (char c : std::string("drive 100"))
      l.push(c, 1);
    l.reset();
    CHECK(l.used == 0);
    CHECK(s.arm(s.token, 20, i));
    CHECK(!s.drive(100, 100, 21));
    CHECK(s.left == 0);
  }
  {
    Sample a, r;
    a.set(1.692f, UINT32_MAX - 20);
    r.set(3.384f, UINT32_MAX - 20);
    float v;
    CHECK(current(a, r, 0, v) && fabs(v) < 1e-5);
    a.value = 1.792f;
    CHECK(current(a, r, 0, v) && fabs(v - 1) < 1e-4);
    a.value = 1.592f;
    CHECK(current(a, r, 0, v) && fabs(v + 1) < 1e-4);
    CHECK(!current(a, r, 500, v));
    r.value = .1f;
    CHECK(!current(a, r, 0, v));
    r.value = 4.0f;
    CHECK(!current(a, r, 0, v));
    r.valid = false;
    CHECK(!current(a, r, 0, v));
    CHECK(adcVoltage(27072, v) && fabs(v - 3.384f) < 1e-5);
    CHECK(!adcVoltage(-1, v));
    CHECK(!adcVoltage(32767, v));
  }
  {
    Sensors s;
    FakeBus b;
    for (int t = 0; t < 300; t++) {
      if (t % 2)
        s.inaStep(b, t);
      else
        s.adsStep(b, t);
    }
    CHECK(s.battery.fresh(300));
    CHECK(fabs(s.battery.value - 12) < 1e-6);
    CHECK(s.analog[2].fresh(300));
    b.fail = true;
    for (int t = 301; t < 500; t++) {
      s.inaStep(b, t);
      s.adsStep(b, t);
    }
    CHECK(!s.battery.valid);
    CHECK(!s.analog[0].valid);
    CHECK(!s.analog[2].valid);
    int before = b.writes + b.reads;
    s.inaStep(b, 501);
    s.adsStep(b, 502);
    CHECK(before == b.writes + b.reads);
    b.fail = false;
    for (int t = 1400; t < 1600; t++) {
      s.inaStep(b, t);
      s.adsStep(b, t);
    }
    CHECK(s.battery.valid);
    CHECK(s.analog[0].valid);
    b.wrongConfig = true;
    for (int t = 1600; t < 1800; t++)
      s.inaStep(b, t);
    CHECK(!s.battery.valid);
  }
  {
    Sensors s;
    FakeBus b;
    b.busy = true;
    s.adsStep(b, 0);
    s.adsStep(b, 2);
    CHECK(s.adsPhase == 1);
    s.adsStep(b, 20);
    CHECK(s.errors == 1 && !s.analog[0].valid);
    for (int t = 0; t < 600; t++)
      s.inaStep(b, t);
    CHECK(!s.battery.valid);
    CHECK(s.errors == 2);
  }
  {
    uint8_t out[32];
    CHECK(feetech::packet(1, 1, nullptr, 0, out) == 6);
    uint8_t ping[] = {255, 255, 1, 2, 1, 251};
    CHECK(!memcmp(out, ping, 6));
    CHECK(feetech::packet(254, 1, nullptr, 0, out) == 0);
    uint8_t p[] = {42, 0, 8};
    CHECK(feetech::packet(1, 3, p, 3, out) == 9);
    CHECK(out[5] == 42 && out[6] == 0 && out[7] == 8);
    feetech::Parser parser;
    uint8_t reply[] = {255, 255, 1, 4, 0, 0, 8, 242};
    for (int j = 0; j < 7; j++)
      CHECK(!parser.push(reply[j]));
    CHECK(parser.push(reply[7]));
    CHECK(parser.bytes[6] == 8);
    parser.reset();
    reply[7]++;
    for (auto c : reply)
      CHECK(!parser.push(c));
    for (int j = 0; j < 100000; j++)
      parser.push(uint8_t(j * 71));
    uint8_t len;
    CHECK(feetech::allowedWrite(40, 0, len));
    CHECK(!feetech::allowedWrite(40, 1, len));
    CHECK(!feetech::allowedWrite(5, 1, len));
    CHECK(!feetech::allowedWrite(42, 2048, len));
    CHECK(feetech::allowedWrite(46, 100, len) && len == 2);
    CHECK(!feetech::allowedWrite(46, 0, len));
  }
  {
    feetech::Goal goals[7];
    for (int j = 0; j < 7; j++)
      goals[j] = {uint8_t(j + 1), uint16_t(2000 + j), 100, 10};
    uint8_t args[58], packet[80];
    size_t n = feetech::syncArgs(goals, 7, args);
    CHECK(n == 58);
    CHECK(args[0] == 41 && args[1] == 7);
    CHECK(args[2] == 1 && args[3] == 10 && args[4] == 0xd0 && args[5] == 7);
    CHECK(args[56] == 100 && args[57] == 0);
    CHECK(feetech::packet(254, 0x83, args, n, packet) == 64);
    uint8_t sum = 0;
    for (int j = 2; j < 64; j++)
      sum += packet[j];
    CHECK(sum == 255);
    CHECK(!feetech::syncArgs(goals, 1, args));
    CHECK(!feetech::syncArgs(goals, 8, args));
    goals[6].id = 1;
    CHECK(!feetech::syncArgs(goals, 7, args));
    goals[6].id = 7;
    goals[6].speed = 0;
    CHECK(!feetech::syncArgs(goals, 7, args));
    Sensors s;
    FakeBus b;
    for (int t = 0; t < 200; t++)
      s.adsStep(b, t);
    CHECK(s.analog[3].fresh(200));
    CHECK(fabs(s.analog[3].value + 0.00025f) < 1e-6);
  }
  {
    Watchdog w;
    w.start(UINT32_MAX - 500);
    CHECK(w.high);
    CHECK(!w.poll(498));
    CHECK(w.poll(499) && !w.high);
    CHECK(!w.poll(10498));
    CHECK(w.poll(10499) && w.high);
    CHECK(w.poll(20499) && !w.high);
  }
  {
    moss::Ramp r;
    CHECK(r.tick(100, 29, 30, 15) == 0);
    CHECK(r.tick(100, 30, 30, 15) == 1);
    CHECK(r.tick(-100, 45, 30, 15) == 0);
    CHECK(r.tick(-100, 144, 30, 15) == 0);
    CHECK(r.tick(-100, 145, 30, 15) == 0);
    CHECK(r.tick(-100, 175, 30, 15) == -1);
    r.stop(180);
    CHECK(r.value == 0);
  }
  printf("PASS %u assertions: state, faults, stale commands, leases, rollover, "
         "lines, sensors, protocol, watchdog, ramp\n",
         checks);
}
