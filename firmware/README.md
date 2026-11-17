# MOSS motor firmware

**QT Py v5:** the current sketch adds a normally closed track-stop input on **SCK / GPIO 36 to GND**, with a latched stop and explicit `clearstop` recovery. Wire the NC contact before updating; an open input prevents track motion. This is software stop support for the tracks and does not cut power or stop the arm. It has been compiled for both drivers and host-tested; a physical button/motor test is required during installation. [Wiring guide](../docs/build/WIRING.md#5-connect-the-two-wire-track-stop-button) · [Firmware and build instructions](MOSS_QTPY_MDD3A/bench/README.md).

**Current: [`MOSS_QTPY_MDD3A/`](MOSS_QTPY_MDD3A/)** (`qtpy-mdd3a-v5`; motor mapping and ramp behaviour retained from v4). The MDD10A build, `-DMOSS_DRIVER_MDD10A`, drives the left track without the drive inversion the MDD3A needed and keeps its encoder inversion. The earlier v4 floor test measured 1.065 m by tape for 1.066 m by the encoders, 5 s at 100 %. QT Py ESP32-S3 on its screw-terminal carrier, native USB, limit 100 %, `ramp` command, one build per driver (Cytron MDD3A by default, `-DMOSS_DRIVER_MDD10A` for the MDD10A). Run `tests/run_qtpy_tests.sh` for the protocol, ramp, stop-loop and GPIO/command integration tests.

**Experimental Core V0.7:** [commissioning firmware and bench console](core-v0.7/README.md) for the new custom PCB. The ESP32-S3 target compiles and passes host tests, but has not been flashed to or validated on an assembled Core board. It uses a dedicated rearm handshake and is not a drop-in replacement for the current QT Py firmware or dimOS arm adapter.

The rest of this page is the V0.3 bench firmware on the DevKitC, kept as history.

## MOSS ESP32-S3 commissioning firmware (V0.3, history)

Reference source snapshot for the firmware restored after the 20 September 2026 bench tests. MAX_PERCENT=25. The temporary 100% firmware is not the default.

Target: Espressif ESP32-S3-DevKitC-1 V1.1. Arduino ESP32 core 3.2.0, ESP32S3 Dev Module, USB CDC On Boot disabled, PSRAM disabled. Use USB-to-UART and 115200 baud with newline-terminated commands.

GPIO mapping: left PWM/DIR 4/5, right PWM/DIR 6/7, left encoder C1/C2 15/16, right encoder C1/C2 17/18. Encoder VCC 3.3 V. Common GND. INA219 SDA/SCL 8/9, VCC 3.3 V, address 0x40.

Commands: status, stop, zero (disarmed only), arm, drive LEFT RIGHT (-25 to +25), test left PERCENT, test right PERCENT. Test commands move one motor for a maximum window of one second. drive commands require arming and must be repeated; a 300 ms command timeout stops/disarms. Ready-to-drive arming expires after 10 seconds. Invalid commands stop/disarm. Motor PWM frequency is 20 kHz; output ramp limiting and reversal dwell are implemented. No automatic movement at boot.

JSON telemetry is emitted approximately every 200 ms. mode: 0=off, 1=ready, 2=drive, 3=timed test. Encoder ticks are raw quadrature x4 counts. No speed PID or conversion to metres is implemented.

INA voltage monitoring is functional. SHUNT_OHMS remains 0 in this flashed reference, so current_mA is null. The physical shunt has since been identified as R100 (0.1 ohm), but current bypassed it in the tested motor harness. Do not enable/use current output as validated motor current without a suitable measurement circuit. Firmware does not provide battery undervoltage cutoff or certified hardware protection.

The source comment stating that shunt resistance is unknown is historical; this snapshot intentionally preserves the flashed source. See the build log for the current hardware decision to use INA219 for voltage only.

Host logic checks: compile tests/control_test.cpp with a C++17 compiler and run the executable. Arduino compilation of this firmware and basic motor/encoder bench operation were completed during commissioning. Hardware watchdog operation under deliberate link failure, loaded operation, and full-rover operation are not established by these bench results.
