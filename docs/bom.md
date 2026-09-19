# Bill of materials (work in progress)

Target: 500 to 700 USD in parts plus a Jetson, before tax and shipping. Prices are not listed yet; they will be once the first unit is complete and the list is stable.

## Printed parts

The authoritative list is the [printed-parts inventory](printed_parts.md) (111 pieces in the reconciled V0.3 print set, per-part material, source file, print job and status; machine-readable copy in `printed_parts.json`). Summary by assembly:

| Assembly | Printed pieces | Notes |
|---|---:|---|
| Body (chassis, motor hatch, bin, cover) | 4 | chassis black PETG (H2S), bin and cover PLA |
| Tracks | 2 | TPU 95A; the 0.8 mm-nozzle track is too stiff, reprint planned |
| Side structure (inner and outer rails, cross spacers) | 8 | PETG |
| Ventilation (splash-proof vent covers) | 2 | PETG |
| Motor mounts | 2 | corrected revision to confirm on the bench |
| Wheels and rollers | 20 | 2 drive wheels (4 halves), 2 idlers (4 halves), 6 road rollers (12 halves) |
| Tensioners and bearing retainers | 12 | |
| Drivetrain spacers | 32 | small spacers, distinct from the 4 cross spacers |
| Gaskets | 3 | TPU |
| Interior supports | 8 | including 4 Jetson base retainers |
| SO-101-derived arm | 8 | clips integrated in the arm parts |
| NC90 gripper (derived from the NormaCore parallel gripper) | 8 | rigid parts |
| Gripper pads | 2 | TPU |
| **Total** | **111** | plus 2 RealSense brackets, printing to confirm |

Not printed: metal HEX12 hubs, bearings, shaft collars, motor–shaft couplings, servo horns, fasteners.

## Electronics
- Jetson Orin Nano 8 GB (brain), in its original plastic base
- Intel RealSense depth camera
- Waveshare controller board
- 2 × Cytron MD10C R3 motor drivers
- 2 × geared DC motors with encoders
- Fuse holder, DC converter, interface modules

## Mechanical hardware
- Steel shafts 5 / 6 / 8 mm (cut to length)
- Bearings 608 and 626 (625 also in stock)
- Shaft collars 5 / 6 / 8 mm
- Rigid couplings 6 mm to 6 mm
- Fasteners M3 and M4

## Arm
- SO-101 derived arm (6 DoF)
- NormaCore parallel gripper

![Hardware ordered](../media/images/build_05_hardware_ordered_20260917.jpg)
