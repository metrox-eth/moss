# Hardware / firmware findings — Core V0.7 commissioning target

Review date: 1 November 2026. Target board SHA-256 supplied by the hardware review:
`456219f7eb97119b7e4328ed76f150012619131788f42d3a9d21fc4e40859cdb`.
Authoritative inputs are `circuit.json` and `MCU_PIN_MAP.json` in the hardware electrical contract, plus the associated power/rearm and watchdog/load timing reviews. The repository contract location is `hardware/electronics/moss-core-v0.7/electrical`; private review checkouts can supply an explicit path. This target is separate from the existing V0.6 firmware.

## Outcome and evidence

A real ESP32-S3 target builds with the installed Arduino core 3.2.0 / CLI 1.1.1. The host suites run the shared safety logic, line parser, sensor drivers, packet codec, watchdog schedule, inherited control/ramp logic and real UART adapter through a simulated UART driver, with AddressSanitizer and UndefinedBehaviorSanitizer. The optional console's drive duration/range validation is also tested without opening a device. `evidence/host_tests.log`, `compile.log` and `manifest.json` record the final result and exact source hashes.

The contract validator checks all 33 connected GPIO roles independently against the hardware JSON and header, plus the critical component identities and signal/sense pins. The final hardware reference is 230 parts; its two JSON hashes are recorded by the validator. No missing MCU pin or demonstrated electronic/firmware incompatibility was identified by these checks. This is a basis for prototype commissioning, not an assertion that the assembled board or rover has passed.

## Concrete issues addressed in the port

| Finding | Resolution |
| --- | --- |
| The legacy firmware name still says MDD3A but its selected MDD10A build is the currently used controller. | Reused its MDD10A PWM/DIR convention, left encoder inversion, quadrature table and ramp. Added a separate V0.7 pin map and target; left the old target untouched. |
| Ready returning after a power dip must not restore a stored drive or UART command. | Dedicated power/ready/commit/latch sequence; every stop clears software intent, drops actuator request, discards pending input/servo work and changes the freshness token. Arm token seeded at boot. |
| GPIO36 is UART OE, not a latch clock. | GPIO1 is the sole ARM_COMMIT output, GPIO2 is input-only readback. U14 is active-high, so software does not invert GPIO36. |
| TPS3431 EN high does not make it permanently active. | SET1 remains low during setup; WDI is high before SET1 rises; first falling edge ≥1 ms later, subsequent falling edges nominally 20 ms apart. The bounded main loop alone feeds it. |
| A 1 ms `millis()` test could yield slightly less than 1 ms at the physical pin. | Commit/clear protocol phases use 2 tick intervals, preserving ≥1 ms despite quantization. Hardware edge quality and delay still need probing. |
| ADC input AIN2 measures a nominal 3.384 V rail, not a hard-coded 3.3 V reference. | Currents use measured rail/2 and 0.1 V/A. Invalid/stale/implausible data becomes null; AIN3 reports signed ground diagnostic without compensation. No uncalibrated protection limits introduced. |
| INA226 shunt terminals are grounded. | Bus-only configuration and measured battery voltage; no invented battery-current/power telemetry. |
| Core 3.2.0 `USBCDC::write()` can spin on a full FIFO even when its lock timeout is zero. | Application queue plus a single nonblocking TinyUSB write, at most 64 bytes per loop. No `Serial.flush()`, whole-line blocking write or dependency on the host draining USB. |
| Releasing UART OE only in the next 1 ms control iteration can overlap a servo's response. | FIFO-only TX, then actual TX_DONE observed with a 1.5 ms absolute polling bound; OE drops before asynchronous reply processing. No software TX queue survives a fault. |
| Single-joint writes are insufficient for the six/seven-servo shoulder arrangement. | Bounded SyncWrite for 2–7 distinct IDs; 64 bytes maximum, no fabricated broadcast acknowledgement. Calibration/mirror transforms remain host responsibilities. |
| Encoder power has a nominal ~17.5 ms ramp. | Ignore startup interrupts for 30 ms and rebaseline phase after enabling power, rather than count the supply transition as movement. This is a software guard, not a measured ramp guarantee. |
| A normal stop changes the token generation but should not look like a fault LED. | LED uses explicit state/reason: stopped/arming slow blink, armed steady, actual fault fast blink. |

## Deliberate scope and limits

- PWM, external watchdog heartbeat, hardware rearming, encoder interrupts, INA226/ADS1115 I²C transactions, half-duplex UART packets and I²S PCM generation have real implementations. No placeholder sensor or actuator success values are returned.
- The host tests cover fault/recovery, unexpected latch, arming failure, queued old token rejection, discarded partial lines, independent drive/USB leases, ready bounce, integer rollover, failed/stalled/recovered I²C, stale/math/saturation handling, grounded ADC signed values, Feetech checksum/ID/error/length/echo handling, UART partial/stuck transmission, asynchronous reply timeout, cancellation, broadcast SyncWrite and legacy reversal/ramp behavior. They cannot establish ISR timing or an electrical waveform.
- UART protocol support is for SMS/STS protocol 0 and the intended STS3215 position mode. Other servo models, EEPROM changes, automatic address discovery, joint calibration, mirrored shoulder calculation, collision avoidance and dimOS autonomy are outside this commissioning firmware. SyncWrite permits simultaneous bus goals; it does not qualify an assembled arm.
- A power request can energize a servo before the firmware can send a torque-off command. The hardware latch restricts new TX and Cytron signals, not a target already stored in a servo or mechanical momentum. Servo boot torque and safe handling need direct tests; no software claim hides this.
- Sensor validity limits are diagnostic. ADC/current offset, gain, shunt temperature effects and amplifier output headroom are uncalibrated. Sequential channel measurements do not equal simultaneous motor-current capture. No battery cutoff, current trip or thermal trip is invented.
- Native USB advertises the installed core's 500 mA descriptor; encoders remain off until USB is configured/open, RF is not started, and audio uses its separate battery branch. Firmware has not proved pre-enumeration/suspend consumption, analog current limiting, or USB compliance. These remain measurements.
- The 100 ms late-loop guard and bounded transactions support the selected watchdog's 170 ms minimum timeout. A whole-program measured worst-case loop time, high-rate encoder ISR stress, USB host abuse and actual UART turnaround under that load are still required.

## Physical checks still required before release claims

No motor, servo, speaker, USB board, power rail or flash operation was accessed in this review. On a real prototype, first verify the configured USB identity/current and all idle outputs; then scope WD_ENABLE/WDI, ACT_READY, ARM_COMMIT, ARM_LATCHED and DRIVE_RUN with dummy loads. Drop and restore the switched actuator rail while the logic/host stays alive and confirm no automatic restart. Measure PWM/DIR polarity, UART OE/data turnaround and servo power-up behavior before connecting a loaded mechanism. Compare battery/rail/ground/current readings to instruments, test encoder polarity under controlled rotation and I²S audio at low amplitude. Supply load steps, regulator stability/temperature, wiring return currents, short/transient behavior and EMI remain separate hardware work.

## Primary references consulted

- [TI ADS1115 datasheet](https://www.ti.com/lit/ds/symlink/ads1115.pdf), input mux, ±4.096 V scaling, OS/config and 860 SPS. Local authoritative PDF/text copies were available in the hardware review.
- [TI INA226 datasheet](https://www.ti.com/lit/ds/symlink/ina226.pdf), bus-only mode, ID registers, conversion-ready flag and 1.25 mV bus LSB.
- [TI TPS3431 datasheet](https://www.ti.com/lit/ds/symlink/tps3431.pdf) and the supplied watchdog boot review, SET1 dynamic disable and first-edge setup/timeout.
- [Feetech SMS/STS register definitions](https://github.com/ftservo/FTServo_Arduino/blob/main/src/SMS_STS.h), [position packet implementation](https://github.com/ftservo/FTServo_Arduino/blob/main/src/SMS_STS.cpp), and [wire packet/SyncWrite implementation](https://github.com/ftservo/FTServo_Arduino/blob/main/src/SCS.cpp). The existing MOSS `moss_dimos/arm_feetech.py` was also read for the current 1 Mbaud/protocol-0 conventions; its higher-level arm behavior was not silently attributed to this target.
- Installed Espressif Arduino 3.2.0 `USBCDC.cpp`, `USB.cpp`, `main.cpp`, IDF UART/I²S headers and the board definition were inspected for the actual compiled APIs and configuration.
