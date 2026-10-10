// Host logic checks for firmware/MOSS_QTPY_MDD3A/Control.h (V0.4):
// the V0.3 protocol cases, plus the configurable ramp.
//   g++ -std=c++17 -o /tmp/control_v04_test tests/control_v04_test.cpp && /tmp/control_v04_test
#include "../MOSS_QTPY_MDD3A/Control.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
using namespace moss;
Reply cmd(Control& c, const char* s, uint32_t t) {
  char line[256]; strcpy(line, s); return c.command(line, t);
}
int main() {
  Control c;
  assert(c.mode == OFF && c.left == 0 && c.right == 0);
  assert(c.rampRiseMs == 30 && c.rampFallMs == 15);
  assert(cmd(c,"drive 10 10",0)==NOT_ARMED);
  assert(cmd(c,"arm",10)==OK);
  assert(cmd(c,"drive 15 -20",20)==OK && c.left==15 && c.right==-20);
  assert(!c.poll(319));
  assert(cmd(c,"status",319)==STATUS);
  assert(c.poll(320) && c.mode==OFF && c.left==0 && c.right==0);
  assert(cmd(c,"drive 1 1",321)==NOT_ARMED);
  assert(cmd(c,"arm",330)==OK);
  assert(cmd(c,"drive 1 1",340)==OK);
  assert(cmd(c,"arm",350)==BUSY && c.mode==OFF);
  const char* invalid[]={"drive 101 0","drive -101 0","drive 1 2 extra","drive 1",
    "drive nan 1","drive 1e2 0","drive 99999999999999999999 0","go","stop x","drive 1 1 x y",
    "ramp 0 10","ramp 501 10","ramp 10","ramp a b"};
  for(auto s: invalid) {
    cmd(c,"arm",0); cmd(c,"drive 20 20",1);
    assert(cmd(c,s,2)==INVALID && c.mode==OFF && !c.left && !c.right);
  }
  // ramp: accepted, bounds inclusive, allowed while moving, does not stop
  cmd(c,"arm",0); cmd(c,"drive 20 20",1);
  assert(cmd(c,"ramp 30 15",2)==OK && c.mode==DRIVE && c.rampRiseMs==30 && c.rampFallMs==15);
  assert(cmd(c,"ramp 1 500",3)==OK && c.rampRiseMs==1 && c.rampFallMs==500);
  assert(cmd(c,"ramp 30 15",4)==OK);
  cmd(c,"stop",5);
  cmd(c,"arm",0); assert(c.poll(10000) && c.mode==OFF);
  cmd(c,"arm",0xfffffff0U); cmd(c,"drive 2 3",0xfffffff5U);
  assert(!c.poll(uint32_t(0xfffffff5U+299U)));
  assert(c.poll(uint32_t(0xfffffff5U+300U)));
  assert(cmd(c,"test left 15",100)==OK && c.left==15 && c.right==0);
  assert(!c.poll(1099)); assert(c.poll(1100) && c.mode==OFF);
  assert(cmd(c,"test right -15",2000)==OK && c.left==0 && c.right==-15);
  assert(cmd(c,"drive 5 5",2001)==NOT_ARMED && c.mode==OFF);
  cmd(c,"test left 15",3000); assert(cmd(c,"stop",3001)==OK && c.mode==OFF);
  cmd(c,"arm",4000); cmd(c,"drive 5 5",4001);
  assert(cmd(c,"zero",4002)==BUSY && c.mode==OFF);
  assert(cmd(c,"zero",4003)==ZERO);

  // ── the ramp, known value in -> known value out ─────────────────────
  Ramp r; uint32_t rise = 30, fall = 15;
  // 0 -> 25 at 30 ms/%: 25 steps, first step at t=30 -> value 25 at t=750
  int v = 0; for (uint32_t t = 0; t <= 750; ++t) v = r.tick(25, t, rise, fall);
  assert(v == 25);
  v = r.tick(25, 749, rise, fall); // no time travel needed: still 25
  // hold: stays 25
  for (uint32_t t = 751; t < 1000; ++t) assert(r.tick(25, t, rise, fall) == 25);
  // 25 -> 0 at 15 ms/%: 25 steps = 375 ms -> zero at t=1375
  for (uint32_t t = 1000; t < 1375; ++t) v = r.tick(0, t, rise, fall);
  assert(v == 0 && r.value == 0);
  // reversal: from +10 to -10 -> falls to 0 (150 ms), dwells 100 ms, then rises
  Ramp q; for (uint32_t t = 0; t <= 300; ++t) q.tick(10, t, rise, fall);
  assert(q.value == 10 && q.sign == 1);
  int last = 10;
  for (uint32_t t = 301; t <= 450; ++t) last = q.tick(-10, t, rise, fall);   // 10 steps of 15 ms from t=300
  assert(last == 0 && q.value == 0 && q.sign == 1);           // reached zero at t=450, direction not flipped yet
  for (uint32_t t = 451; t < 550; ++t) assert(q.tick(-10, t, rise, fall) == 0);  // 100 ms dwell
  assert(q.tick(-10, 550, rise, fall) == 0 && q.sign == -1);  // direction flips at t=550, no step yet
  assert(q.tick(-10, 579, rise, fall) == 0);                   // rise slope counts from the flip
  assert(q.tick(-10, 580, rise, fall) == -1);
  int after = 0; for (uint32_t t = 581; t <= 900; ++t) after = q.tick(-10, t, rise, fall);
  assert(after == -10 && q.sign == -1);
  // slope change mid-ramp: 1 ms/% rise -> 25 % in 25 ms
  Ramp s; int w = 0; for (uint32_t t = 0; t <= 25; ++t) w = s.tick(25, t, 1, 15);
  assert(w == 25);
  // rollover-safe stepping
  Ramp o; o.lastStep = 0xffffffe0U; int z = o.tick(5, 0xffffffe0U + 30U, 30, 15);
  assert(z == 1);
  printf("control_v04_test: OK (protocol + ramp)\n");
  return 0;
}
