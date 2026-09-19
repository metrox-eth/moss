#include "../MOSS_ESP32S3/Control.h"
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
  const char* invalid[]={"drive 26 0","drive -26 0","drive 1 2 extra","drive 1",
    "drive nan 1","drive 1e2 0","drive 99999999999999999999 0","go","stop x","drive 1 1 x y"};
  for(auto s: invalid) {
    cmd(c,"arm",0); cmd(c,"drive 20 20",1);
    assert(cmd(c,s,2)==INVALID && c.mode==OFF && !c.left && !c.right);
  }
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
  Ramp r;
  for(uint32_t t=10; t<=250; t+=10) assert(r.tick(25,t)==int(t/10));
  for(uint32_t t=260; t<=500; t+=10) assert(r.tick(-25,t)==25-int((t-250)/10));
  for(uint32_t t=510; t<600; t+=10) assert(r.tick(-25,t)==0);
  assert(r.tick(-25,600)==-1);
  r.stop(601); assert(r.value==0);
  assert(r.tick(25,650)==0);
  assert(r.tick(25,701)==1);
  assert(r.tick(0,702)==0 && r.value==0);
  puts("PASS: arming, invalid inputs, timeout, rollover, test duration, stop, encoder reset gating, reversal dwell");
}
