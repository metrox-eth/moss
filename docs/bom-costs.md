# MOSS parts budget — prototype and Raspberry Pi experiments

**21 September 2026 · USD · hardware prototype V0.3**

This comparison replaces the initial $500–700 target excluding the Jetson. It values reused hardware at replacement cost so that a new builder can see the scope. It is not the prototype's actual cash expenditure, a supplier quote, or a validated kit BOM. The [current hardware inventory](bom.md) and [113-piece print inventory](printed_parts.md) remain separate references.

## Three configurations

| Budget category | Prototype: Jetson + D455 | Pi 5 + Mighty | Pi 5 + ST ToF |
|---|---:|---:|---:|
| Shared mechanics, arm/gripper, drive, control and power | $480 | $480 | $480 |
| Computer, cooling and computer-specific power | $480 | $203 | $203 |
| Storage | $250: 2 TB SSD allowance | $15: 128 GB microSD | $15: 128 GB microSD |
| Sensors and dedicated connections | $466 | $122 | $123 |
| **Estimated total** | **$1,676** | **$820** | **$821** |
| Optional Hailo AI HAT+ | — | +$70 | +$70 |

The video rounds the prototype to **about $1,680**. The two Pi columns are alternatives, not a combined sensor stack. Neither contains a Jetson, RealSense or 2D lidar. Both retain a colour camera for litter detection. The prototype retains its 2 TB SSD; the Pi budgets use microSD only.

**The $250 SSD amount is an unverified allowance**, not a confirmed model or paid price. Change it dollar-for-dollar when the actual value is available. Of the $856 difference between prototype and Pi/Mighty, $235 comes from changing storage. With a $15 storage allowance on both sides, the difference would be $621. No equivalent navigation or inference performance has been demonstrated.

## Shared parts — $480

All amounts below are estimates or rounded budget allowances. Quantities are planning quantities; confirm them against the final assembly before purchasing. The CF35-12 allowance rounds a $49.99 supplier listing. Servo gearing and motor specifications still need exact purchasable references.

| Item | Quantity | Unit / lot USD | Line USD |
|---|---:|---:|---:|
| Espressif ESP32-S3-DevKitC-1 | 1 | 13 | 13 |
| Waveshare Bus Servo Adapter (A) V1.1 | 1 | 5 | 5 |
| Cytron MD10C R3 motor driver | 2 | 18 | 36 |
| 12 V geared DC motor with quadrature encoder | 2 | 15 | 30 |
| ST3215 12 V arm joint servo | 5 | 22 | 110 |
| CF35-12 constant-force gripper servo | 1 | 50 | 50 |
| Assembled 3S battery with BMS, replacement allowance | 1 | 35 | 35 |
| Compatible 12.6 V CC/CV charger | 1 | 12 | 12 |
| Accessible motor/servo power cut, fuse holders, fuses and distribution | 1 lot | 18 | 18 |
| Power/signal wiring, XT60, ferrules, terminals and heat-shrink | 1 lot | 15 | 15 |
| USB control cables for ESP32 and servo adapter | 1 lot | 10 | 10 |
| INA219 battery-voltage monitor | 1 | 5 | 5 |
| Bearings: 12 × 625, 4 × 608, 4 × 626 | 20; lot budget | 12 | 12 |
| Shaft collars: 12 × Ø5, 4 × Ø8, 2 × Ø6 mm | 18; lot budget | 18 | 18 |
| Shaft stock: Ø5 × 500, Ø6 × 250, Ø8 × 250 mm | 1 of each; lot | 8 | 8 |
| Rigid Ø6–Ø6 mm couplings, Ø14 × 22 mm envelope | 2 | 2.5 | 5 |
| Compatible metal hex wheel hubs | 2 | 1.5 | 3 |
| Screws, nuts, washers, inserts and small spacers | 1 lot | 15 | 15 |
| Black PETG filament | 2 kg | 18 | 36 |
| PLA filament | 1 kg | 14 | 14 |
| TPU 95A filament | 1 kg | 25 | 25 |
| Enclosure ventilation, fan/filter/grille | 1 lot | 5 | 5 |
| **Shared total** | | | **480** |

- The arm budget is **five ST3215 joint servos plus one CF35-12 for the MOSS gripper**. It is not the standard SO-101 servo set.
- Battery and charger are replacement allowances. The prototype uses a reused pack; this table does not establish its capacity, BMS thresholds or runtime. A future pack design needs its own qualification.
- The INA219 line budgets voltage monitoring. The prototype's R100 shunt is bypassed by motor current; this is not a main-rail current measurement design.
- The power/distribution allowance does not specify a final whole-robot fuse rating. The existing 5 A bench-test rating is not a completed rover rating.
- Filament amounts budget whole spools, not measured part masses. Use the print inventory for each part's material; buying lots of fasteners or bearings may cost more than the consumed quantities shown here.
- Shaft stock, hub fits and fasteners must be checked against the assembled revision. These budget lines do not replace cutting drawings. Remove the hub allowance if hubs are included with the motors. The prototype's earlier hardware order is already represented by these lines; do not add its entire order total again.

Shared category subtotals used in the video: arm/gripper $160; motors/drivers $66; mechanics/filament $136; control/power/wiring/ventilation $118.

## Compute and storage

| Item | Prototype | Each Pi option | Price basis |
|---|---:|---:|---|
| Jetson Orin Nano Super 8 GB kit, cooling included | $480 | — | Current sourcing reference reported by the builder |
| Raspberry Pi 5 8 GB | — | $175 | Selected budget reference; PiShop listing |
| Active Pi cooler | — | $8 | Estimate |
| Battery-to-Pi regulated supply, target 5.1 V / 5 A continuous | — | $20 | Estimate; module and interface not qualified |
| 2 TB SSD | $250 | — | Allowance; model and paid price unconfirmed |
| 128 GB A2 microSD | — | $15 | Estimate |
| **Compute, cooling, specific power and storage** | **$730** | **$218** | |

The Jetson boots from the prototype battery in the reported assembly. No extra Pi-specific converter is charged to that column. The Pi needs a suitable power path for both board and peripherals; verify voltage, current capability and USB-C current recognition where applicable. The $20 allowance is not approval of an arbitrary buck converter.

## Sensor options

| Item | Prototype | Pi + Mighty | Pi + ST | Price basis |
|---|---:|---:|---:|---|
| RealSense D455, RGB and IMU included | $466 | — | — | Builder's paid price |
| Mighty Camera, onboard IMU | — | $92 | — | Paid price; ordered 21 September |
| STEVAL-VL53L9 evaluation board | — | — | $80 | Paid price; ordered 21 September |
| Fixed colour USB UVC camera | — | $25 | $25 | Estimate |
| Separate compatible IMU | — | — | $8 | Estimate |
| Dedicated sensor connection / adaptation | — | $5 | $10 | Estimate; ST adapter not yet identified |
| **Sensor subtotal** | **$466** | **$122** | **$123** | |

**Mighty:** onboard visual-inertial pose estimation, with a monochrome tracking camera and IMU. Its loop-closure feature is documented as beta and disabled by default; it should not be treated as a proven persistent map. Obstacle mapping and integration with dimOS on the Pi remain to be tested. The separate RGB camera is for colour litter detection.

**ST:** the VL53L9CX evaluation board provides 3D ToF depth, with 2.3K zones and a manufacturer-stated range up to 9 m under suitable conditions. It is a forward depth sensor, not a 360° 2D scanner or a complete SLAM system. Localisation would combine encoders, an IMU and geometric/visual correction. Pi driver, MIPI/I3C connection, acquisition, power and RGB/depth calibration remain to be qualified. The supplier estimates one unit in stock on **28 October 2026**; that is not a guaranteed delivery date.

Both sensors were ordered; neither alternative navigation configuration has been validated on MOSS. dimOS is the intended software stack for the experiments. Test detection rate, tracking drift, low obstacles, outdoor behaviour, RAM use and thermal limits before describing either as a reproducible navigation build.

## Optional accelerator and exclusions

A **Raspberry Pi AI HAT+ 13 TOPS (Hailo-8L)** adds a $70 budget reference: **$890 / $891** with Mighty / ST. It is optional. It needs a compatible detector and software stack; it does not automatically accelerate mapping or replace CUDA across the application.

A wrist camera, gamepad, tools, printer, labour, development computer, electricity and API/service usage are not included in any column. Additional shipping, import costs and taxes are not added; reported paid prices may already contain some charges that are not itemised. Most lines are estimates, so allow a separate contingency before buying. This is a component budget, not a selling price.

## Sources and price provenance

Accessed for the 21 September comparison; prices and availability vary by location.

- [Raspberry Pi 5 8 GB — PiShop](https://www.pishop.us/product/raspberry-pi-5-8gb/): $175 budget reference retained for both Pi builds.
- [Raspberry Pi AI HAT+](https://www.raspberrypi.com/products/ai-hat/): optional 13 TOPS board.
- [Mighty documentation](https://mightycamera.com/docs), [SDK](https://mightycamera.com/docs/sdk) and [development history](https://mightycamera.com/story).
- [STEVAL-VL53L9 — STMicroelectronics](https://www.st.com/en/evaluation-tools/steval-vl53l9.html): evaluation board specifications and interfaces.
- [CF35-12 — Waveshare](https://www.waveshare.com/product/robotics/motors-servos/servos/cf35-12.htm): rounded $50 allowance.
- [Waveshare Bus Servo Adapter (A)](https://docs.waveshare.com/Bus_Servo_Adapter_A): interface reference.
- Jetson $480: builder-reported current price. RealSense $466, Mighty $92 and ST $80: builder-reported paid prices, not guaranteed retail offers. A separately reported Thai Jetson quote of 19,600 THB is not treated as equivalent to $480.
- All other amounts, including the $250 SSD, are allowances rather than verified purchase prices.

## Media

[45-second video](../media/video/MOSS_cost_comparison_20260921.mp4) · [Poster](../media/images/MOSS_cost_comparison_20260921.jpg) · [Media credits](../media/MOSS_cost_comparison_20260921_credits.md)
