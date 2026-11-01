# MOSS Core V0.7 commissioning firmware

Prototype commissioning target, 1 November 2026. This is a separate target for **ESP32-S3-WROOM-1U-N8**, Cytron **MDD10A**, and the current Core V0.7 circuit. It does not replace the working V0.6/QT Py release. This target has not been flashed or tested on a powered board; it is not hardware-qualified.

The motor ramp, quadrature decoder and established MDD10A direction convention come from the current `MOSS_QTPY_MDD3A` firmware (its MDD10A build option), not the older ESP32S3 target. `LegacyControl.h` preserves that source; the new safety state machine replaces its arm/test handling. License: Apache-2.0.

## Build and offline checks

Tested toolchain: Arduino CLI **1.1.1**, Espressif Arduino core **3.2.0**. No third-party Arduino libraries. Flash 8 MB, PSRAM disabled, native USB-OTG/TinyUSB CDC, 20 kHz / 10-bit motor PWM. No Wi-Fi/BLE initialization; both controllers are stopped/disabled during setup.

From this folder:

```sh
./tools/test_host.sh
./tools/compile.sh
```

The exact compiler invocation used on the review machine was:

```sh
'/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli' \
  --config-file "$HOME/.arduinoIDE/arduino-cli.yaml" compile --warnings all \
  --fqbn 'esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=8M,PSRAM=disabled,PartitionScheme=default_8MB' \
  --build-path ./fw_build/esp32s3 ./src/MOSS_CORE_V07
```

`compile.sh` supports `ARDUINO_CLI` and `ARDUINO_CONFIG` overrides. All build products stay in `fw_build`; no upload command is provided or run. Host tests run with AddressSanitizer/UndefinedBehaviorSanitizer, exercise the real portable state/sensor/protocol headers and real UART transport against a simulated driver, and retain the prior ramp/control regression tests. Four deliberately corrupted copies of the electrical contract verify that the validator rejects GPIO, ADC-address, UART-OE-part and shunt-value drift. The contract is discovered at `hardware/electronics/moss-core-v0.7/electrical` in a containing repository, with a private-review `design/electrical` fallback. Override with `MOSS_ELECTRICAL=/path/to/electrical ./tools/test_host.sh` or `python3 tools/validate_contract.py --electrical /path/to/electrical`. `validate_contract.py` independently compares the GPIO header with a reviewed mapping, `MCU_PIN_MAP.json`, component MPNs and relevant pins in `circuit.json`.

## State and rearming

At startup PWM, command enables, actuator power request, commit, encoder power, audio enable and watchdog enable are low. Peripheral setup finishes before the watchdog starts. WDI goes high before SET1/`WD_ENABLE`; its first falling edge is at least 1 ms later, then falling edges occur nominally every 20 ms in the main loop. SET1 low really disables this TPS3431 watchdog; EN remains tied high. No interrupt or background task feeds it.

`arm TOKEN` consumes the current one-use token. It raises **ACT_POWER_ENABLE only**, waits for ACT_READY to remain high for 10 ms, then qualifies clear release and generates a dedicated GPIO1 pulse. Each pulse/margin phase waits 2 millisecond ticks, ensuring at least 1 ms despite `millis()` quantization. GPIO2 must confirm ARM_LATCHED. Motor and UART commands stay inhibited until this completes. DRIVE_RUN readback has a 2 ms software settling allowance and a mismatch stops the session.

The token starts from `esp_random()` at boot and changes on every stop/fault; it is a freshness nonce, **not authentication**. A stale `arm TOKEN` cannot restart the current session. Fault handling clears targets, ramps, incomplete input, unsent receive bytes, pending servo work, actuator power and audio. There is no automatic retry/rearm or command restoration. Recover by reading the new status and explicitly arming again. State numbers: 0 stopped, 1 waiting for rail, 2 clear margin, 3 commit high, 4 commit low, 5 armed, 6 driving.

All active states require `keepalive` or a valid drive/servo command more often than every **300 ms**. A drive request independently expires after **300 ms**, even if keepalives continue. Status/ramp/tone queries do not refresh motion. Arming has a separate 1000 ms rail deadline. USB close, unplug or suspend, USB power fault, loss of ready/latch, unexpected gate state, malformed/overflowed serial input, failed servo transaction or a late active loop stop the session. Sensor faults invalidate measurements but impose no uncalibrated voltage/current protection threshold.

The circuit independently gates motor signals and UART TX and clears the latch on qualified hardware faults. This software cannot prove mechanical stopping, servo torque state, or cancellation inside a powered servo. Cutting actuator power is not a mechanical brake. A servo may retain/recover a prior target or enable torque at power-up before any UART command; establish its actual power-up behavior on the prototype.

## Bench console and USB protocol

The optional POSIX console uses only Python's standard library and opens hardware **only when an operator explicitly runs it**:

```sh
python3 tools/bench_console.py /dev/cu.usbmodemYOUR_DEVICE
```

It has no automatic reconnect or rearm. Type `arm` after a fresh stopped status; the console supplies the token and sends 100 ms keepalives. In this console, `drive LEFT RIGHT MILLISECONDS` repeats drive commands for 1–5000 ms and then sends `stop`. Ctrl-C/EOF sends a best-effort stop and exits. The firmware lease remains the fallback if USB is gone. A servo operation can move a mechanism: start with individual unloaded servos and supported tracks during later physical commissioning.

The raw device protocol is ASCII, newline terminated, maximum 255 characters per line; partial lines expire after 100 ms. Open CDC with DTR asserted (115200 is the nominal line coding). Commands and responses share the port with JSON telemetry every 200 ms. Hosts must distinguish `OK`/`ERR` from JSON and tolerate dropped telemetry when they do not read the port.

| Raw command | Behavior |
| --- | --- |
| `status` | Current state, freshness token, gate inputs, counters and measured values. |
| `arm TOKEN` | Fresh deliberate power/ready/commit/latch sequence. Bare `arm` is only a console shorthand. |
| `keepalive` | Refresh active-session lease; never refreshes the independent drive deadline. |
| `drive L R` | Signed -100..100 percent, armed state required. Repeat <300 ms; defaults ramp 30/15 ms per percent, 100 ms reverse dwell. |
| `stop` | Immediate PWM zero and actuator permission/power removal; replaces token. |
| `zero` | Reset encoder counters, stopped state only. |
| `ramp UP DOWN` | 1..500 ms per percentage point; inherited behavior. |
| `servo ping ID` | Unicast Feetech ping, response checked. |
| `servo read ID ADDRESS LENGTH` | Address 0..70, length 1..8, final address ≤70; raw bytes, no fabricated conversion. |
| `servo write ID ADDRESS VALUE` | SRAM whitelist only: 40=0 (torque off), 41=1..254 (acceleration), 46=1..1500 (speed, little endian). |
| `servo torque ID 0` | Acknowledged torque-off command. |
| `servo torque ID 1` | Read position 56/57, reject outside 0..4095, preload current position with speed 100 and acceleration 10, then enable torque. All three replies required. |
| `servo move ID POSITION SPEED ACC` | Write registers 41..47 atomically: ACC, 0..4095 position, goal time zero, speed 1..1500. ACC 1..254. Does not enable torque. |
| `servo syncmove ID POS SPEED ACC ID POS SPEED ACC ...` | 2–7 distinct IDs; same per-servo limits as move. One broadcast SyncWrite of registers 41..47, 24–64 bytes total. Response says `transmitted:true, acknowledged:false`; broadcast has no reply. |
| `tone HZ MS PERCENT` | 100..4000 Hz, 1..2000 ms, 1..10% full-scale PCM, 16 kHz stereo-identical I²S. Can run while stopped; stop/disconnect/fault cancels it. |

IDs are 1..253. There are no EEPROM/ID/baud/mode/calibration writes, no blind UART bridge and no old bypassing `test` command. One servo transaction at a time; `OK servo_pending` acknowledges acceptance, not completion. Unicast completion reports `acknowledged:true` only after correct ID, length, checksum and zero servo error status. Timeout/error stops the session; no retry. SyncWrite confirms transmission only; verify each servo afterward using reads.

The supported command layout is Feetech **SMS/STS protocol 0**, 1 Mbaud, little endian, intended for the current STS3215 arm in position mode. Configure and verify model, baud, position mode and response level before using motion; this build does not identify an unknown servo model or transform SCSCL/wheel-mode register semantics. Numerical position bounds are protocol bounds, not calibrated joint limits. SyncWrite supports the six-servo arm and optional seventh shoulder servo at the bus layer; the host must supply calibrated mirrored positions and check mechanical limits/twin errors. It does not provide the dimOS manipulator, collision avoidance, calibration, or automatic torque sequencing for an assembled arm.

## Interfaces and measurements

| Interface | Implemented contract and remaining check |
| --- | --- |
| MDD10A | GPIO18/17 left PWM/DIR, GPIO9/8 right. Positive uses DIR low, inherited measured convention. Hardware gates both through DRIVE_RUN. Confirm final harness direction on bench. |
| Encoders | Left A/B 7/6; right 5/16, original quadrature table, left tick inversion retained. GPIO42 supply enabled only with open/configured USB. Ignore 30 ms startup ramp and rebaseline phases; actual supply rise and count accuracy need measurement. |
| Watchdog/latch | GPIO47 SET1, 48 WDI, 38 power, 39 ready, 1 commit, 2 latched, 44 drive gate feedback. GPIO2 is input without internal pull. |
| INA226 | U17 address 0x40, verified manufacturer/die ID and config, register 0 = 0x4126 bus-only continuous; conversion-ready checked. Battery register 2 ×1.25 mV. IN+/IN− are grounded: battery current/power is intentionally absent. |
| ADS1115/INA240 | U43 0x48, single shots at 860 SPS, ±4.096 V, 125 µV/count. Read back config and wait for OS completion. AIN0/1 motor sense; AIN2 measured logic rail; AIN3 signed grounded-input diagnostic. |
| Current calculation | `current_A = (sense_V - rail_V/2) / (50 × 0.002)`; nominal rail is **3.384 V**, not assumed 3.300 V. No learned offset or invented calibration. Rail outside 3.0..3.6 V invalidates the ADC set as implausible measurement; this is a validity bound, not an actuator protection threshold. |
| Servo electrical | GPIO35 TX, 37 RX, 36 transmit enable. U14 is **active-high** SN74LVC2G126, no software polarity inversion. Hardware still qualifies OE with ready/latch/watchdog/reset. Local echo is discarded; RX is enabled by ACT_READY. |
| Audio | GPIO10 BCLK, 11 LRCLK, 12 DATA, 13 enable to MAX98357A through existing buffers. SD_MODE high enables; identical L/R samples work with selected channel. I²S writes have zero wait, and digital amplitude is not a measured speaker power limit. AMP_5V has no MCU feedback. |
| Status | GPIO15 LED: slow blink while stopped/arming, solid armed/driving, fast blink after a fault. ESTOP_ACTIVE high also holds hardware reset, so a continuously pressed stop normally prevents firmware telemetry. |

`battery_V`, `rail_V`, `sense_V`, `adc_ground_V` and `current_A` are `null` when invalid or ≥500 ms old. A current additionally requires a fresh plausible rail and sense within that rail. Values are sequential samples, not simultaneous capture. `adc_ground_V` is diagnostic only and is never subtracted as an invented correction. `ticks`, `invalid_edges`, `target_pct`, `output_pct`, `ramp_ms`, `act_ready`, `arm_latched`, `drive_run`, `usb_power_fault`, `i2c_errors`, `max_loop_us` and `tx_drops` support initial bring-up.

## Bounded operations and qualification boundary

The main loop reads at most 64 USB bytes, writes at most 64 USB bytes with one nonwaiting TinyUSB call, processes one sensor register operation, services at most 64 servo RX bytes and submits at most 128 PCM frames with zero wait. The I²C timeout is 5 ms (conservatively ≤10 ms for a register read). USB output has a 4096-byte application queue and drops complete outgoing lines when full. There is no host-dependent USB flush/wait.

UART has a 256-byte RX buffer and no software TX queue. A command is at most 64 bytes in the 128-byte FIFO; after writing it, software observes actual TX_DONE with a **1.5 ms hard polling deadline** and immediately lowers OE, before waiting up to 20 ms asynchronously for a response. It never leaves the transmitter enabled until the next millisecond tick. Faults close the hardware gate and abandon pending requests. The UART must be fully idle before another transmission. This bounded polling approach must still be measured with the actual servo response timing and interrupt load.

The active-session loop stops on a ≥100 ms iteration gap; the external TPS3431 supplies the independent reset boundary (170 ms minimum selected timeout). Bounds above describe code and API behavior, not a measured worst-case execution time on the new board. USB enumeration/pre-enumeration current, supply transitions, DFF/clear pulse waveforms, driver output glitches, servo power-up motion, RF-off consumption, I²S sound, UART electrical levels, EMI and load/thermal behavior remain physical tests. Firmware cannot certify the PCB for production or replace those checks.

See `HARDWARE_FIRMWARE_FINDINGS.md` and `evidence/manifest.json` for the recorded source/build evidence. Local detailed logs are kept in `evidence/` and excluded from Git because toolchains include local filesystem paths.
