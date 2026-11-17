#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <initializer_list>
#include <string>

#define ARDUINO_ISR_ATTR
#define DRAM_ATTR
#define LOW 0
#define HIGH 1
#define INPUT_PULLUP 2
#define OUTPUT 3
#define RISING 4
#define CHANGE 5
using gpio_num_t = int;
using portMUX_TYPE = int;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(x) ((void)(x))
#define portEXIT_CRITICAL(x) ((void)(x))
#define portENTER_CRITICAL_ISR(x) ((void)(x))
#define portEXIT_CRITICAL_ISR(x) ((void)(x))

constexpr int A0=18, A1=17, A2=9, A3=8, SDA=7, SCL=6, TX=5, RX=16;
constexpr int SDA1=41, SCL1=40, SCK=36;
inline uint32_t stubNow = 0;
inline int stubPins[64] = {};
inline uint32_t stubPwm[64] = {};
inline void (*stubInterrupts[64])() = {};
inline int stubInterruptMode[64] = {};
inline uint32_t millis() { return stubNow; }
inline void delay(uint32_t n) { stubNow += n; }
inline void pinMode(int, int) {}
inline int digitalRead(int p) { return stubPins[p]; }
inline void digitalWrite(int p, int v) { stubPins[p] = v; }
inline int gpio_get_level(int p) { return stubPins[p]; }
inline bool ledcAttach(int, uint32_t, int) { return true; }
inline bool ledcWrite(int p, uint32_t v) { stubPwm[p]=v; return true; }
inline bool ledcDetach(int) { return true; }
inline void noInterrupts() {}
inline void interrupts() {}
inline void attachInterrupt(int p, void (*fn)(), int mode) {
  stubInterrupts[p]=fn; stubInterruptMode[p]=mode;
}
inline void stubInput(int p, int value) {
  int old=stubPins[p]; stubPins[p]=value;
  if (stubInterrupts[p] && old != value &&
      (stubInterruptMode[p] == CHANGE || value == HIGH)) stubInterrupts[p]();
}

struct SerialStub {
  std::string output, input;
  explicit operator bool() const { return true; }
  bool dtr() const { return true; }
  void begin(int) {}
  void setTxTimeoutMs(int) {}
  int availableForWrite() const { return 4096; }
  int available() const { return int(input.size()); }
  int read() { char c=input[0]; input.erase(0,1); return c; }
  size_t write(const uint8_t* p, size_t n) { output.append((const char*)p,n); return n; }
  size_t write(char c) { output+=c; return 1; }
};
inline SerialStub Serial;
