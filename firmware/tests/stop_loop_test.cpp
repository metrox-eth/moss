#include "../MOSS_QTPY_MDD3A/StopLoop.h"
#include "../MOSS_QTPY_MDD3A/Control.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
using namespace moss;

int main() {
  StopLoop s;
  assert(s.blocked());  // An unsampled input cannot enable motion.
  s.sample(false, 0);
  assert(!s.blocked()); // Correctly closed NC contact at boot, still disarmed.
  Control c;
  char arm[] = "arm", drive[] = "drive 50 50";
  assert(c.command(arm, 0) == OK);
  assert(c.command(drive, 1) == OK);
  s.sample(true, 2);    // Button press or broken loop wire.
  if (s.blocked()) c.stop("stop_open");
  assert(c.mode == OFF && c.left == 0 && c.right == 0);
  assert(s.blocked() && !s.clear(1000));
  s.sample(false, 1001);
  assert(s.blocked() && !s.clear(1100));
  assert(s.clear(1101) && !s.blocked());
  assert(c.mode == OFF && c.left == 0 && c.right == 0);

  // A short rising edge remains latched even if the next sample is closed.
  s.trip(1200); s.sample(false, 1200);
  assert(s.blocked());
  assert(!s.clear(1299)); assert(s.clear(1300));
  // Reopening during the release debounce restarts its entire interval.
  s.sample(true, 1300); s.sample(false, 1301);
  s.sample(true, 1350); s.sample(false, 1351);
  assert(!s.clear(1450)); assert(s.clear(1451));
  // Open at boot is latched; a reset cannot convert a pressed stop to READY.
  StopLoop boot; boot.sample(true, 0);
  assert(boot.blocked() && !boot.clear(10000));
  boot.sample(false, 10001);
  assert(boot.blocked() && !boot.clear(10100));
  assert(boot.clear(10101));
  // millis() rollover preserves the release interval.
  StopLoop wrap; wrap.sample(true, 0xfffffff0U);
  wrap.sample(false, 0xfffffff5U);
  assert(!wrap.clear(uint32_t(0xfffffff5U + 99U)));
  assert(wrap.clear(uint32_t(0xfffffff5U + 100U)));
  puts("stop_loop_test: OK (boot, opening, latch, release, bounce, rollover)");
}
