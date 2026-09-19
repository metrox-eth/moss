# MOSS ESP32-S3 commissioning firmware

Reference source snapshot for the firmware restored after the 20 September 2026 bench tests. MAX_PERCENT=25. The temporary 100% firmware is not the default.

Target: Espressif ESP32-S3-DevKitC-1 V1.1. Arduino ESP32 core 3.2.0, ESP32S3 Dev Module, USB CDC On Boot disabled, PSRAM disabled. Use USB-to-UART and 115200 baud with newline-terminated commands.

GPIO mapping: left PWM/DIR 4/5, right PWM/DIR 6/7, left encoder C1/C2 15/16, right encoder C1/C2 17/18. Encoder VCC 3.3 V. Common GND. INA219 SDA/SCL 8/9, VCC 3.3 V, address 0x40.

Commands: status, stop, zero (disarmed only), arm, drive LEFT RIGHT (-25 to +25), test left PERCENT, test right PERCENT. Test commands move one motor for a maximum window of one second. drive commands require arming and must be repeated; a 300 ms command timeout stops/disarms. Ready-to-drive arming expires after 10 seconds. Invalid commands stop/disarm. Motor PWM frequency is 20 kHz; output ramp limiting and reversal dwell are implemented. No automatic movement at boot.

JSON telemetry is emitted approximately every 200 ms. mode: 0=off, 1=ready, 2=drive, 3=timed test. Encoder ticks are raw quadrature x4 counts. No speed PID or conversion to metres is implemented.

INA voltage monitoring is functional. SHUNT_OHMS remains 0 in this flashed reference, so current_mA is null. The physical shunt has since been identified as R100 (0.1 ohm), but current bypassed it in the tested motor harness. Do not enable/use current output as validated motor current without a suitable measurement circuit. Firmware does not provide battery undervoltage cutoff or certified hardware protection.

The source comment stating that shunt resistance is unknown is historical; this snapshot intentionally preserves the flashed source. See the build log for the current hardware decision to use INA219 for voltage only.

Host logic checks: compile tests/control_test.cpp with a C++17 compiler and run the executable. Arduino compilation of this firmware and basic motor/encoder bench operation were completed during commissioning. Hardware watchdog operation under deliberate link failure, loaded operation, and full-rover operation are not established by these bench results.
