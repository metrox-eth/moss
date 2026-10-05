# Bench scripts for the V0.4 board

Run from the onboard computer the QT Py is plugged into. They need `pyserial` and `esptool` in the Python used (`PY` at the top of `flash_qtpy.sh`).

- `flash_qtpy.sh`: puts the QT Py in its ROM bootloader through the native USB, writes the four images produced by `arduino-cli compile --fqbn esp32:esp32:adafruit_qtpy_esp32s3_nopsram:CDCOnBoot=cdc --output-dir <dir>` (plus `boot_app0.bin` from the ESP32 core), then resets the chip with the RTC watchdog. A plain RTS reset leaves the chip in the bootloader, the watchdog reset does not.
- `moss_bench.py "test left 15"`: sends one command and prints the telemetry lines that follow (mode, output, encoder ticks, battery). Start with `test left 15`, then `test right 15`, rover on blocks. At 5 % the motors do not start.
- `servo_scan.py`: pings every ID on the arm's servo bus (Feetech SMS_STS, 1 Mbps) and reads model, position, voltage and temperature of each servo that answers.
- `servo_watch.py` / `watch_start.sh`: logs which servo moves while you move the arm by hand (torque off), to map IDs to joints before assigning them.
