// Read-only consumer of the candidate headers; no firmware source is rewritten.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include "Core.h"
#include "Sensors.h"
using namespace core07;
unsigned checks=0;
#define VERIFY(c) do { ++checks; assert(c); } while(0)
Inputs healthy(){ Inputs i{}; i.usb=true; return i; }
uint32_t completeArm(Safety& s, Inputs& i, uint32_t at){
  VERIFY(s.arm(s.token,at,i));
  i.ready=true; s.poll(at+1,i); s.poll(at+11,i); s.poll(at+13,i);
  VERIFY(s.commit()); i.latch=true; s.poll(at+15,i); s.poll(at+17,i);
  VERIFY(s.armed()); VERIFY(s.left==0 && s.right==0); return at+17;
}
int main(){
  // Every observed fault must invalidate the previous arm token and target.
  for(unsigned fault=0;fault<6;fault++){
    Safety s; Inputs i=healthy(); uint32_t old=s.token;
    uint32_t t=completeArm(s,i,100); VERIFY(s.drive(80,-40,t));
    if(fault==0)i.ready=false;
    if(fault==1)i.latch=false;
    if(fault==2)i.estop=true;
    if(fault==3)i.usbFault=true;
    if(fault==4)i.usb=false;
    if(fault==5)i.pwmOK=false;
    s.poll(t+1,i); VERIFY(!s.active()); VERIFY(!s.driveEnable());
    VERIFY(s.left==0 && s.right==0); VERIFY(s.token!=old);
    i=healthy(); i.ready=true; i.latch=false;
    VERIFY(!s.arm(old,t+2,i)); VERIFY(!s.drive(80,-40,t+2));
    s.poll(t+3,i); VERIFY(!s.active());
    uint32_t next=completeArm(s,i,t+10);
    VERIFY(s.left==0 && s.right==0 && !s.driveEnable());
    VERIFY(s.drive(10,0,next)); VERIFY(s.driveEnable());
  }
  // WD first falling edge follows SET1 setup, then falling edges stay below170ms.
  Watchdog wd; wd.start(100); VERIFY(!wd.poll(1099)); VERIFY(wd.high);
  VERIFY(wd.poll(1100)); VERIFY(!wd.high);
  uint32_t lastFall=1100; unsigned falls=1;
  for(uint32_t t=1101;t<2000000;t++)if(wd.poll(t)&&!wd.high){
    VERIFY(t-lastFall<170000); lastFall=t; ++falls;
  }
  VERIFY(falls>50);
  // PGA±4.096V, single shot, 860SPS, AIN0/1/2 versusGND.
  Sensors sensor;
  for(unsigned c=0;c<3;c++){
    sensor.channel=c; auto cfg=sensor.adsConfig();
    VERIFY(((cfg>>12)&7)==4+c); VERIFY(((cfg>>9)&7)==1);
    VERIFY((cfg&(1u<<8))!=0); VERIFY(((cfg>>5)&7)==7);
  }
  // Ratiometric zero and signed1A with gain50 ×2mΩ, not INA226 current register.
  Sample signal,rail; rail.set(3.384f,100); float amps;
  for(int a=-10;a<=10;a++){
    signal.set(1.692f+0.1f*a,100); VERIFY(current(signal,rail,100,amps));
    VERIFY(amps>a-.0001f && amps<a+.0001f);
  }
  printf("PASS %u independent assertions; observed faults, fresh arm, watchdog, ADS config, current scale\n",checks);
}
