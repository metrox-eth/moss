#pragma once
#include <stdint.h>
struct WireStub {
  void begin(int,int,int) {}
  void setTimeOut(int) {}
  void beginTransmission(uint8_t) {}
  void write(uint8_t) {}
  int endTransmission(bool=true) { return 1; } // Sensor absent in this motor-stop test.
  int requestFrom(uint8_t,uint8_t) { return 0; }
  int read() { return 0; }
};
inline WireStub Wire1;
