# Bill of materials (work in progress)

The initial $500–700 target excluding the Jetson has been superseded by an [itemized comparison dated 21 September 2026](bom-costs.md): approximately **$1,680 for the Jetson / RealSense prototype configuration**, including an estimated $250 for its 2 TB SSD, and **$820 / $821 for experimental Pi 5 configurations** using Mighty Camera / ST 3D ToF and microSD storage.

These are planning budgets using replacement values for reused hardware, not a receipt total. Additional tax and shipping are not added. The Pi configurations are not yet navigation-tested; the hardware inventory below continues to describe the V0.3 prototype.

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
- Jetson Orin Nano Super 8 GB (brain), retaining its original plastic base; Wi-Fi on the Jetson side
- 2 TB SSD
- Intel RealSense D455 depth camera (RGB and IMU included)
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

## V0.4 selection (next revision, not built)

The next revision selects a QT Py ESP32-S3 (5426), screw-terminal BFF (6495), optional enclosure (6505), INA219 STEMMA QT (904) and 300 mm cable (5384). One set is **$39.60** including the enclosure, before shipping and import charges. A Cytron MDD3A is selected to replace the two MD10Cs. The Waveshare Bus Servo Adapter remains.

See [the V0.4 update](hardware_v04.md) for quantities, unit prices, CAD status and remaining fit checks. This does not overwrite the as-built V0.3 inventory above. The new Adafruit INA footprint still needs reconciliation with the current hull model.

## Mechanical hardware
- Steel shafts 5 / 6 / 8 mm (cut to length)
- Bearings 608 and 626 (625 also in stock)
- Shaft collars 5 / 6 / 8 mm
- Rigid couplings 6 mm to 6 mm
- Fasteners M3 and M4

## Arm
- SO-101-derived arm: five ST3215 12 V joint servos
- NormaCore-derived parallel gripper: one CF35-12 constant-force servo
- This is the MOSS servo configuration, not the unmodified six-servo SO-101 kit BOM.

![Mechanical hardware](../media/images/build_05_hardware_ordered_20260917.jpg)
