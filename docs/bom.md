# Bill of materials (work in progress)

Target: 500 to 700 USD in parts plus a Jetson, before tax and shipping. Prices are not listed yet; they will be once the first unit is complete and the list is stable.

## Printed parts

The authoritative list is the [printed-parts inventory](printed_parts.md) (113 pieces in the V0.3 print set, per-part material, source file and print job; machine-readable copy in `printed_parts.json`). Summary by assembly:

| Assembly | Printed pieces | Notes |
|---|---:|---|
| Body (chassis, motor hatch, bin, cover) | 4 | chassis black PETG (H2S), bin and cover PLA |
| Tracks | 2 | TPU 95A, 0.4 mm nozzle profile (a 0.8 mm-nozzle print came out too stiff) |
| Side structure (inner and outer rails, cross spacers) | 8 | PETG |
| Ventilation (splash-proof vent covers) | 2 | PETG |
| Motor mounts | 2 | corrected revision Ø31 / M3 |
| Wheels and rollers | 20 | 2 drive wheels (4 halves), 2 idlers (4 halves), 6 road rollers (12 halves) |
| Tensioners and bearing retainers | 12 | |
| Drivetrain spacers | 32 | small spacers, distinct from the 4 cross spacers |
| Gaskets | 3 | TPU |
| Interior supports | 8 | including 4 Jetson base retainers |
| SO-101-derived arm | 8 | clips integrated in the arm parts |
| NC90 gripper (derived from the NormaCore parallel gripper) | 8 | rigid parts |
| Gripper pads | 2 | TPU |
| Camera brackets | 2 | RealSense D455 |
| **Total** | **113** | |

Not printed: metal HEX12 hubs, bearings, shaft collars, motor–shaft couplings, servo horns, fasteners.

## Electronics (as selected on 20 September 2026, after the first harness bench tests)
- Jetson Orin Nano 8 GB (brain), in its original plastic base; Wi-Fi on the Jetson side
- Intel RealSense depth camera (the IMU comes from it)
- Espressif ESP32-S3-DevKitC-1 V1.1: motor controller (PWM/DIR for both drivers, both quadrature encoders, I²C to the INA219); see [`firmware/`](../firmware/README.md) for the wiring map
- 2 × Cytron MD10C R3 motor drivers
- 2 × geared DC motors with quadrature encoders
- Waveshare Bus Servo Adapter (A) V1.1: separate interface for the SO-101 arm servos (arm not tested yet)
- INA219 module at 0x40 (R100 = 0.1 Ω shunt): used for battery voltage only. In the tested wiring the motor current bypasses the shunt, so its current readings are not motor consumption. See the build log.
- Fuse holder with automotive blade fuse, 5 A (32 V DC) for the motor bench tests. The rating for the complete rover with Jetson and arm is not set yet; the pack's BMS thresholds are unknown.
- Positive distribution terminal block with ferrules; negative returns chained; XT60 to the pack
- 5 V buck converter for the logic, if needed (not installed)
- Removed from the design: Waveshare General Driver for Robots.

Cabling: same wire for the main runs and the driver branches, runs of 25–30 cm at most. Conductor bundle measured 1.2 mm in diameter; section estimated at 0.75–1 mm², not manufacturer-verified.

## Mechanical hardware
- Steel shafts 5 / 6 / 8 mm (cut to length)
- Bearings 608 and 626 (625 also in stock)
- Shaft collars 5 / 6 / 8 mm
- Rigid couplings 6 mm to 6 mm
- Fasteners M3 and M4

## Arm
- SO-101 derived arm (6 DoF)
- NormaCore parallel gripper

![Mechanical hardware](../media/images/build_05_hardware_ordered_20260917.jpg)
