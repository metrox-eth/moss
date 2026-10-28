# Bill of materials — R92

One rover, using separate off-the-shelf modules. Choose one computer and one depth camera.

[Download the purchasing list as CSV](docs/build/MOSS_BOM.csv).

## Control and audio

| Item | Quantity | Note |
|---|---:|---|
| Adafruit QT Py ESP32-S3, 8 MB flash, no PSRAM, ref.5426 | 1 |  |
| Adafruit Terminal Block BFF, ref.6495 | 1 |  |
| Adafruit INA219 STEMMA QT, ref.904 | 1 |  |
| STEMMA QT cable, 300 mm, ref.5384 | 1 |  |
| Cytron MDD10A Rev2 dual motor driver | 1 |  |
| Waveshare Bus Servo Adapter A | 1 |  |
| MAX98357A amplifier module | 1 |  |
| Speaker, 3 W, 4 ohm | 1 |  |
| Acoustic splash membrane and compatible adhesive | 1 | EPTFE or non woven fabric membrane. |

## Drive

| Item | Quantity | Note |
|---|---:|---|
| JGB37-520, 12 V, 90:1, 110 rpm, Hall encoder, 6 mm D-shaft | 2 |  |
| 625 bearing | 12 |  |
| 608 bearing | 4 |  |
| 626 bearing | 4 |  |
| LK05 — shaft collar, 5 mm bore, Ø10 × 5 mm | 12 |  |
| LK06 — shaft collar, 6 mm bore, Ø11 × 5 mm | 2 |  |
| LK08 — shaft collar, 8 mm bore, Ø16 × 8 mm | 4 |  |
| Smooth steel axle, 5 ×70 mm finished length | 6 | Check the physical stack before cutting stock. |
| Smooth steel axle, 6 ×77 mm finished length | 2 |  |
| Smooth steel axle, 8 ×87 mm finished length | 2 |  |
| Rigid motor-to-shaft coupling, 6 mm bores | 2 |  |
| HEX12 metal wheel hub, 6 mm bore, 18 mm length | 2 |  |

LK05/LK06/LK08 are guide identifiers for purchased shaft collars, also called lock rings. [All spacer and collar references](docs/build/PART_REFERENCES.md).

## Arm, gripper and body

| Item | Quantity | Note |
|---|---:|---|
| ST3215 12 V serial bus servo | 5 | Keep the original servo screw packs. |
| CF35-12 constant-force gripper servo | 1 |  |
| 3010 fan, 12 V | 2 |  |
| Magnet, 20 ×10 ×2 mm | 4 | Glue into the pockets with epoxy; check polarity before gluing. |
| Small two-part epoxy adhesive kit, two tubes (resin + hardener) | 1 kit | For gluing the four bin magnets and joining the two-piece hull and cover when printing on a smaller printer. |
| M3 brass heat-set insert, OD4 mm, length 6 mm | 11 | 10 in the hull and 1 in the LiDAR base. |

## Power and wiring — module-based rover

**Optional custom battery:** [3S4P / twelve EVE 21700 cells — parts and illustrated build](hardware/power/custom-3s4p-battery/). Its rated capacity is 20 Ah and assembled mass is 910 g; usable capacity and runtime are not yet measured. The 110 × 67 × 35 mm dimensions below refer to the earlier compact pack, **not** this custom build. Choose one battery solution; do not add both to the shopping list.

| Item | Quantity | Note |
|---|---:|---|
| 12-cell battery pack, 3S4P, with BMS | 1 | 110 × 67 × 35 mm. |
| 12.6 V CC/CV charger for the selected 3S pack | 1 |  |
| Emergency stop LA16-11ZS/A, 16 mm | 1 |  |
| KCD11 two-pin rocker switch and splash cover | 1 |  |
| Inline blade-fuse holder, 14 AWG | 1 |  |
| ATC blade fuse, 15 A | 1 |  |
| Amass XT30 male/female connector pair | 6 |  |
| DC panel socket, 5.5 ×2.1 mm | 2 | Female panel-mount sockets. |
| DC male barrel plug — computer power branch | 1 | Jetson: **5.5 × 2.5 mm**, 9.5 mm barrel, centre positive ([NVIDIA specification](https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_carrier_board_specification_sp.pdf)). Pi option: choose the plug that matches the input of the selected 5 V power supply. These are alternatives. |
| DC male barrel plug, 5.5 × 2.1 mm — servo power branch | 1 | For the Waveshare Bus Servo Adapter A ([Waveshare specification](https://docs.waveshare.com/Bus_Servo_Adapter_A)). |
| DC male barrel plug, 5.5 × 2.1 mm — battery extension | 1 | Matches the 5.5 × 2.1 mm panel socket listed above. |
| Wire, ferrules and heat-shrink | 1 lot |  |
| Hoco HB1 four-port USB 2.0 hub | 1 |  |
| GameSir Nova 2 Lite gamepad with wireless USB receiver | 1 | For manual driving; include the wireless USB receiver. Used successfully on MOSS. |
| USB-C to USB-A cable, 30 cm | 3 |  |
| RealSense camera cable | 1 | [Lazada product link](https://www.lazada.co.th/products/i16248699269-s127506585857.html) · RealSense option only. |

## Choose one computer

| Item | Quantity | Note |
|---|---:|---|
| NVIDIA Jetson Orin Nano Super Developer Kit | 1 | Use the Jetson carrier. |
| OR Raspberry Pi5 with its cooler, storage and appropriate 5 V supply | 1 | Use the Pi carrier and the mounting screws and spacers supplied with the HAT. |

## Sensors

| Item | Quantity | Note |
|---|---:|---|
| Intel RealSense D455 OR Orbbec Gemini 2 | 1 | Use the matching printed insert(s); these are alternatives. |
| SLAMTEC RPLIDAR C1 | 1 |  |
| Wrist USB camera for the R30 mount | 1 | PCB mounting-hole pattern: 21 × 13.5 mm. |

## Fasteners by assembly

Quantities are for one rover. Use the assembly step to locate each fastener.

| Assembly | Fasteners for one rover |
|---|---|
| Choose the hull and fit the inserts | 11 × M3 heat-set insert, OD4 mm, length 6 mm; 6 × Split hull only: M4 × 15 socket-head screw; 6 × Split hull only: M4 hex nut, 7 mm across flats; 6 × Split hull only: M4 washer, Ø9 × 0.8 mm |
| Build the six road wheels | 18 × M3 × 35 socket-head screw; 18 × M3 hex nut |
| Build the two drive wheels | 6 × M3 × 20 socket-head screw; 6 × M3 hex nut |
| Build the two idler wheels | 6 × M3 × 25 socket-head screw; 6 × M3 hex nut |
| Fit the motors and inner bearing retainers | 8 × M4 × 20 socket-head screw; 8 × M4 hex nut; 12 × M3 × 8 socket-head screw |
| Fit the inner track frames | 6 × M4 × 15 socket-head screw; 6 × M4 hex nut |
| Fit the drive axles and outer bearing covers | 6 × M3 × 15 socket-head screw; 6 × M3 hex nut |
| Fit the idler slides and tensioners | 16 × M3 × 15 socket-head screw; 16 × M3 hex nut; 4 × M4 × 35 socket-head screw; 8 × M4 hex nut; 4 × M4 washer |
| Close the track frames | 4 × M4 × 60 socket-head screw; 4 × M4 hex nut; 4 × M4 washer |
| Fit the driver and controller | 4 × M3 × 6 socket-head screw; 6 × M2 × 6 screw, non-countersunk; 6 × M2 washer, 0.3 mm thick |
| Fit the speaker and amplifier | 2 × M3 × 6 socket-head screw; 2 × M2 × 6 screw, non-countersunk; 2 × M2 washer, 0.5 mm thick |
| Fit the computer carrier and servo adapter | 2 × M3 × 6 socket-head screw; 2 × M3 × 8 socket-head screw; 4 × M3 washer, 0.5 mm thick; 4 × M2.5 × 8 screw, non-countersunk; 4 × M2.5 washer, 0.5 mm thick; 2 × Jetson only: M3 × 8 socket-head screw, no washer |
| Fit the camera option | 2 × RealSense only: M4 × 10 socket-head screw; 2 × Gemini only: M3 × 8 socket-head screw |
| Fit the LiDAR carriage | 2 × M3 × 10 socket-head screw; 4 × M2.5 × 6 socket-head screw; 1 × M3 × 20 socket-head screw |
| Fit power distribution and cooling | 4 × M2.5 × 10 low-head screw, head diameter 5 mm maximum |
| Fit the arm plate and build the arm | 4 × M3 × 10 socket-head screw; 4 × M4 × 25 countersunk 90-degree screw; 4 × M4 hex nut; 20 × Kit screw: M2 × 6, original servo head; 37 × Kit screw: M3 × 6, original servo head |
| Build the gripper and wrist camera | 11 × Kit screw: M3 × 6 cross-head ISO7045; 6 × Kit screw: #1-42 x3/16 inch typeAB; 4 × M2 × 6 screw, non-countersunk, for wrist camera PCB; 2 × M3 × 10 socket-head screw, for wrist camera bracket; 2 × M3 hex nut, for wrist camera bracket |
| Close the hull and fit the bin | 10 × M3 × 10 countersunk 90-degree screw, head diameter 6.4 mm maximum; 4 × M3 × 10 countersunk 90-degree screw, head diameter 5.6 mm maximum |

Screw lengths are measured under the head, except countersunk screws, which use their full length. Retain the original heads supplied with the servo and gripper kits. Camera screw sets are alternatives.

[Measured fastener lengths](docs/build/FASTENER_MEASUREMENTS.md). Pi/HAT mounting hardware is supplied with the HAT; no separate screw purchase is added.

The supplied computer carriers are for the NVIDIA Jetson Orin Nano and Raspberry Pi 5. Choose one carrier and one camera option.

See the [assembly cards](docs/build/ASSEMBLY.md).

## Adhesive for the split hull and cover

Use the same two-part epoxy kit listed above. Retain the six M4 hull fixings and the four cover mounting screws.
