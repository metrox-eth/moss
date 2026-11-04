# Power behavior and rearming

MOSS Core V0.7 prototype, updated 1 November 2026. This describes the proposed circuit and its firmware interface. It is not a report of a powered-board test.

## Power paths

The Cytron and arm draw from the switched battery rail. The Orange Pi has its own MP9447 converter branch. Core's ESP32 and logic receive USB power through J1, a protected input and a TLV62569 regulator. These branches share ground and, in the normal rover assembly, ultimately use the same battery. They are **not galvanically isolated**.

The net named `3V3` is nominally **3.384 V**, set by R70 = 464 kΩ and R71 = 100 kΩ. The existing input/output capacitors and local IC decoupling remain in place. C170 adds 6.8 pF across R70, following TI's recommendation for a 100 kΩ lower feedback resistor. This feedforward capacitor is intended to improve transient response. It does not provide battery hold-up, remove shared-ground interference or establish measured stability. Its populated value must be checked with load steps on the prototype. See the [TLV62569 datasheet, section 8.2.2.2](https://www.ti.com/lit/ds/symlink/tlv62569.pdf).

U20 supervises the logic supply. U27 qualifies the switched actuator rail. A loss of actuator voltage can occur while the USB-powered logic remains alive, so a logic reset cannot be assumed every time a motor supply fault occurs.

## Why the authorization latch was added

Previously, if the actuator rail fell and recovered while the processor retained its enable outputs and PWM command, `ACT_READY` could return high and reopen the command gates. Recovery of the supply alone could therefore resume the previous electrical commands.

U51, a TI SN74LVC1G74DCUR flip-flop, now remembers a deliberate arm pulse. U52, a TI SN74HCS11PWR Schmitt-input gate, clears that memory when the actuator rail is not ready, reset is asserted, watchdog authorization is withdrawn, or the actuator power request is withdrawn. Schmitt inputs are used for the slow supervisor signals. Returning to valid conditions does not itself clock U51.

The resulting gates are:

```text
ARM_CLEAR_N = ACT_READY & RESET_N & WD_ENABLE & ACT_POWER_ENABLE
ARM_READY   = ACT_READY & ARM_LATCHED & ACT_POWER_ENABLE
DRIVE_RUN   = WD_ENABLE & DRIVE_ENABLE & ARM_READY & RESET_N
SERVO_OE_ON = WD_ENABLE & SERVO_TX_ENABLE & ARM_READY & RESET_N
```

`ARM_COMMIT` uses ESP32 GPIO1; `ARM_LATCHED` is read back on GPIO2. GPIO1 reaches U51 through R230, with a pull-down at the clock input. `ACT_POWER_ENABLE` remains independent of the latch, allowing the rail to rise and become ready before arming. The serial transmit-enable signal is not reused as the arm clock.

## Firmware sequence

1. Start with PWM zero, `DRIVE_ENABLE`, `SERVO_TX_ENABLE`, `ACT_POWER_ENABLE`, `WD_ENABLE` and `ARM_COMMIT` low.
2. Establish healthy watchdog operation and request actuator power while keeping the command enables low. Wait for `ACT_READY` to settle. A missing ready indication is a fault, not a reason to force the latch.
3. After a fresh arm request and valid conditions, keep the clear-release conditions stable, then pulse `ARM_COMMIT`. A 1 ms software margin and a 1 ms high/low pulse are conservative protocol values, not measurements of the assembled circuit. Verify `ARM_LATCHED` before enabling commands.
4. On a fault, discard the previous movement request and lower the command enables. Recovery requires a new arm sequence. A held-high commit output is not a new edge.

The [Core commissioning firmware](https://github.com/metrox-eth/moss/tree/main/firmware/core-v0.7) implements this interface with a one-use arm token and GPIO44 gate feedback. Its clear/commit phases use two millisecond ticks to preserve at least 1 ms despite timer quantization. The existing rover controller firmware is not a drop-in substitute. `WD_ENABLE` drives TPS3431 SET1 as well as the command gates. SET1 low disables the watchdog timer even though its EN pin is tied high; this permits startup and ROM flashing with the GPIO held low by R12. EN stays high so its ENOUT output does not hold the processor in reset. When SET1 rises, allow the documented 150 µs setup interval, then supply falling edges on WDI comfortably before the selected timeout minimum (170 ms). Use a bounded main-loop heartbeat, not an independent timer that could keep feeding a stalled control loop. See [TPS3431 sections 7.3.2.4 and 8.3.2.4](https://www.ti.com/lit/ds/symlink/tps3431.pdf).

The latch inhibits **Cytron command signals and new servo UART transmission**. It does not prove that a powered servo has forgotten an earlier command, mechanically brake the arm, eliminate motor regeneration, or guarantee a zero-duration output glitch under every analog fault. Servo power-up/torque behavior and command cancellation require separate commissioning. Clock/clear coincidences outside the flip-flop timing requirements remain unqualified.

## Motor wiring and noise

Each motor plug carries two winding wires and four encoder wires. The copper circuits are separate even though they share a cable jacket. J2 brings the Cytron's winding outputs back to Core's shunts and onward to J3/J4. These winding leads are H-bridge outputs, not ground wires.

J11 is the intended main Cytron supply connection. J2.5 and J11.2 both connect to Core ground; if the driver also joins those grounds, they form parallel returns. The signal-ground wire cannot be assumed to carry exactly zero power current. Keep the main supply pair low impedance and qualify the complete harness under load. Do not remove the logic reference ground without redesigning and validating the interface.

## Routing changes and validation limits

This update chamfers selected actual right-angle bends on USB, audio, encoder and ADC routes. A segment oriented at 45° or 90° does not by itself tell us the angle of the turn into the next segment. Existing load-path widths and motor shunt connections are preserved.

For fast signals, the reference plane, loop area, nearby switching nodes and discontinuities matter alongside corner geometry. Two 45° turns are a useful routing convention; counting corners alone is not an EMI test. See [TI's high-speed layout guidance](https://www.ti.com/lit/pdf/scaa082), [motor-driver layout guidance](https://www.ti.com/lit/pdf/slva959), and [Espressif's ESP32-S3 USB layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html).

The release evidence separates netlist/PCB consistency, digital state-model tests, geometry checks and existing bounded analog analyses. No whole-rover mixed-signal or electromagnetic simulation is claimed.

On the first assembled boards, record the logic and host supply voltages, reset/ready/latch signals and encoder counts while motors start, stop and reverse under controlled load with the final harness. Exercise actuator-rail loss and recovery without issuing a new arm request. Check current-sense zero/gain, regulator load response and temperatures before using the result as a basis for a batch.
