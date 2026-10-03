# Bill of materials

**Estimates, retail, one rover.** Checked against the V0.5 CAD on 1 October 2026. Prices in USD; a line marked *paid* is what we actually paid, the others are listings or allowances. A kit will cost less: filament by the gram instead of the spool, servos and bearings in volume.

## Totals

| | Kit base | Jetson + RealSense | Pi + Hailo + Gemini |
|---|---:|---:|---:|
| Kit base (everything below) | 482 | 482 | 482 |
| Computer | | 730 | 218 |
| AI accelerator | | on board | 232 |
| Depth camera | | 466 | 234 |
| 2D lidar | | 72 | 72 |
| **Total** | **about $480** | **about $1,750** | **about $1,240** |

The Jetson configuration is the prototype. The Pi configuration is drawn, not yet run.

## Computer and perception

| Item | Qty | USD | Note |
|---|---:|---:|---|
| NVIDIA Jetson Orin Nano Super 8 GB | 1 | 480 | plus a 2 TB NVMe SSD, allowance 250 |
| Intel RealSense D455 | 1 | 466 | *paid*. Depth from 0.12 m with the current close-range software |
| USB 3.1 C to A cable, 90° plug with locking screws, 0.3 m | 1 | 7 | *paid*. The straight plug does not fit in the hull |
| Raspberry Pi 5 8 GB | 1 | 175 | with active cooler 8, 5 V supply 20, microSD 15 |
| Raspberry Pi AI HAT+ 2 (Hailo-10H, 40 TOPS) | 1 | 232 | *paid*; list price about 200 |
| Orbbec Gemini 2 | 1 | 234 | listing. Depth from 0.15 m, 91° × 66° |
| SLAMTEC RPLIDAR C1 | 1 | 72 | listing (RobotShop, DFRobot). Mount printed; position on the cover still being settled |

## Kit base, about $482

| Block | USD |
|---|---:|
| Control electronics | 49 |
| Drive | 30 |
| Arm and gripper | 160 |
| Power and wiring | 90 |
| Mechanical hardware | 61 |
| Filament | 87 |
| Fans and magnets | 5 |

### Control electronics

| Item | Qty | Unit | Line | Note |
|---|---:|---:|---:|---|
| Adafruit QT Py ESP32-S3, 8 MB flash, no PSRAM (5426) | 1 | 12.50 | 12.50 | *paid* |
| Adafruit Terminal Block BFF (6495) | 1 | 10.95 | 10.95 | *paid*. Screw terminals instead of jumper wires |
| Adafruit INA219 STEMMA QT (904) | 1 | 9.95 | 9.95 | *paid*. Battery voltage only |
| STEMMA QT cable, 300 mm (5384) | 1 | 1.25 | 1.25 | *paid* |
| Cytron MDD3A dual motor driver, 4–16 V, 3 A per channel | 1 | 9.53 | 9.53 | listing |
| Waveshare Bus Servo Adapter (A) | 1 | 5 | 5 | estimate |

### Drive

| Item | Qty | Unit | Line | Note |
|---|---:|---:|---:|---|
| 12 V geared DC motor with quadrature encoder | 2 | 15 | 30 | estimate; exact reference to pin with the files |

### Arm and gripper

| Item | Qty | Unit | Line | Note |
|---|---:|---:|---:|---|
| ST3215 12 V bus servo | 5 | 22 | 110 | arm joints |
| CF35-12 constant-force servo | 1 | 50 | 50 | gripper |

The small camera in the hand (Waveshare 38 mm USB camera in the CAD) is not priced yet.

### Power and wiring

| Item | Qty | Unit | Line | Note |
|---|---:|---:|---:|---|
| 3S lithium pack with BMS | 1 | 35 | 35 | allowance; pack not specified yet |
| 12.6 V CC/CV charger | 1 | 12 | 12 | estimate |
| Emergency stop (16 mm, LA16-11ZS/A), fuse holder, fuses, distribution | lot | 18 | 18 | e-stop *paid* 2.23 |
| Wiring, ferrules, heat-shrink, 2 × DC 5.5 × 2.1 mm panel sockets | lot | 15 | 15 | sockets *paid* 1.51 each |
| XT30 pairs: one input, four outputs (arm, computer, driver, fans) | 5 | | | not priced yet; printed housing |
| USB cables for the controller and the servo adapter | lot | 10 | 10 | estimate |

### Mechanical hardware

| Item | Qty | Note |
|---|---:|---|
| Bearings 625 | 12 | two per roller |
| Bearings 608 | 4 | two per idler wheel |
| Bearings 626 | 4 | motor side and outer |
| Shaft collars Ø5, Ø6, Ø8 bore | 12, 2, 4 | Ø8 *paid* 2.14 each |
| Shafts: Ø5 × 80 (6), Ø6 × 90 (2), Ø8 × 100 (2) mm | 10 | cut from Ø5 × 500, Ø6 × 250, Ø8 × 250 mm bars |
| Rigid motor-to-shaft couplings, Ø6 bores | 2 | |
| HEX12 metal wheel hubs, Ø6 bore, 18 mm | 2 | drop if supplied with the motors |

Bearings about 12, collars 18, bars 8, couplings 5, hubs 3, screws 15: about $61.

Screws in the drivetrain: M3 × 16 (22), M3 × 20 (6), M3 × 25 (6), M3 × 35 (18), M4 × 16 (6), M4 × 40 (4), M4 × 60 (4), M2.5 × 10 (4); 52 M3 nuts, 18 M4 nuts (4 lock nuts), 8 M4 washers. The hull hatch and the arm add M3 positions whose lengths are fixed with the files.

### Filament

| Filament | Qty | Unit | Line | Note |
|---|---:|---:|---:|---|
| PETG, black | 2 kg | 10.39 | 20.79 | *paid* |
| PLA, matte | 2 kg | 20.64 | 41.27 | *paid* |
| TPU 95A | 1 kg | 25 | 25 | tracks and pads |

The sliced hull, cover, bin and brackets alone use 1.15 kg of PETG and 1.1 kg of PLA. See [3D printing](3DPrinting.md).

### Fans and magnets

| Item | Qty | Unit | Line | Note |
|---|---:|---:|---:|---|
| 3010 fan, 12 V | 2 | 1.68 | 3.35 | *paid*. Rear extraction |
| Magnet 20 × 10 × 2 mm | 4 | 0.43 | 1.73 | *paid*. Two in the cover, two in the bin |
