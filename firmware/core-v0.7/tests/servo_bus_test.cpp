// SPDX-License-Identifier: Apache-2.0
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <stdint.h>
#include <vector>
#define LOW 0
#define HIGH 1
uint32_t us = 0;
bool oe = false, stuck = false, partial = false, initFail = false;
unsigned waits = 0;
std::deque<uint8_t> incoming;
std::vector<uint8_t> transmitted;
void digitalWrite(int, bool value) { oe = value; }
uint32_t micros() { return us += 10; }
#include "ServoBus.h"
int uart_param_config(int, const uart_config_t *) { return initFail ? -1 : 0; }
int uart_set_pin(int, int, int, int, int) { return 0; }
int uart_driver_install(int, int, int, int, void *, int) { return 0; }
int uart_flush_input(int) {
  incoming.clear();
  return 0;
}
int uart_wait_tx_done(int, int) {
  waits++;
  return stuck && oe ? -1 : 0;
}
int uart_tx_chars(int, const char *b, uint32_t n) {
  transmitted.assign(b, b + n);
  for (auto c : transmitted)
    incoming.push_back(c);
  return partial ? int(n) - 1 : int(n);
}
int uart_read_bytes(int, uint8_t *b, int, int) {
  if (incoming.empty())
    return 0;
  *b = incoming.front();
  incoming.pop_front();
  return 1;
}
unsigned checks = 0;
#define CHECK(x)                                                               \
  do {                                                                         \
    checks++;                                                                  \
    if (!(x)) {                                                                \
      fprintf(stderr, "FAIL %d: %s\n", __LINE__, #x);                          \
      abort();                                                                 \
    }                                                                          \
  } while (0)
void response(uint8_t id, uint8_t err, std::initializer_list<uint8_t> data) {
  uint8_t b[32];
  std::vector<uint8_t> v(data);
  auto n = feetech::packet(id, err, v.data(), v.size(), b);
  for (size_t j = 0; j < n; j++)
    incoming.push_back(b[j]);
}
int main() {
  ServoBus b;
  CHECK(b.begin());
  CHECK(b.start(1, 1, nullptr, 0, 0, 100));
  CHECK(!oe && b.busy);
  CHECK(!b.start(2, 1, nullptr, 0, 0, 100));
  response(1, 0, {});
  b.poll(101);
  CHECK(b.done && b.success && !b.busy);
  CHECK(!oe);
  CHECK(b.start(2, 2, (const uint8_t *)"8\2", 2, 2, 200));
  response(3, 0, {1, 2});
  response(2, 0, {0, 8});
  b.poll(201);
  CHECK(b.done && b.success);
  CHECK(b.length == 2 && b.data[1] == 8);
  CHECK(b.start(1, 1, nullptr, 0, 0, 300));
  response(1, 4, {});
  b.poll(301);
  CHECK(b.done && !b.success && b.error == 4);
  CHECK(b.start(1, 1, nullptr, 0, 0, 400));
  b.poll(419);
  CHECK(b.busy);
  b.poll(420);
  CHECK(b.done && !b.success && !oe);
  CHECK(b.start(1, 1, nullptr, 0, 0, UINT32_MAX - 10));
  b.poll(8);
  CHECK(b.busy);
  b.poll(9);
  CHECK(b.done && !b.success);
  partial = true;
  CHECK(!b.start(1, 1, nullptr, 0, 0, 500));
  CHECK(!oe && !b.busy);
  partial = false;
  stuck = true;
  unsigned before = waits;
  CHECK(!b.start(1, 1, nullptr, 0, 0, 500));
  CHECK(waits - before < 160);
  CHECK(!oe && !b.busy);
  stuck = false;
  CHECK(b.start(1, 1, nullptr, 0, 0, 600));
  b.abort();
  CHECK(!b.busy && !b.done && !oe && incoming.empty());
  b.poll(601);
  CHECK(!b.done);
  CHECK(b.start(1, 2, (const uint8_t *)"8\2", 2, 2, 700));
  response(1, 0, {1});
  b.poll(701);
  CHECK(b.done && !b.success);
  feetech::Goal goals[7];
  for (int j = 0; j < 7; j++)
    goals[j] = {uint8_t(j + 1), 2048, 100, 10};
  uint8_t params[58];
  auto n = feetech::syncArgs(goals, 7, params);
  CHECK(b.start(254, 0x83, params, n, 255, 800));
  CHECK(b.done && b.success && !b.busy && !b.acknowledged && !oe);
  CHECK(transmitted.size() == 64);
  initFail = true;
  ServoBus bad;
  CHECK(!bad.begin());
  CHECK(!bad.start(1, 1, nullptr, 0, 0, 0));
  printf("PASS %u assertions: real ServoBus adapter, echo, id, errors, "
         "timeout, rollover, TX partial/stall, cancel\n",
         checks);
}
