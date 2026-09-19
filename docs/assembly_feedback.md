# Assembly feedback — V0.3 prototype

One line per finding: what was observed, which part and revision, what was done on the prototype, what is planned for the next revision, and what validation actually happened. Nothing here is a completed drive test.

| Finding | Part / revision | On the prototype | Next revision | Validation done |
|---|---|---|---|---|
| TPU track too stiff | Track printed with a 0.8 mm nozzle | Not used; the 0.4 mm profile (nozzle, extrusion width, walls, layer height, infill, material) is the reference | Record the full print profile with the part | 0.4 mm track: manual floor test, good flexibility and grip |
| Motor mounts | Corrected brackets Ø31 / M3 (files marked V2-01) | Check screw depth at assembly | — | Not yet |
| Motor mount to hull joint | Through-hole planned on the prototype | Drill through | Real through-joint designed in | Not yet |
| Front of the cover and offset arm plate | Cover, arm plate | Keep the unfinished interface as is | Complete-cover study, parked | — |
| Camera brackets | Two RealSense D455 brackets | Fit at assembly | — | Not yet |
| Plate gasket | R8 gasket listed with the R11 plate | Check the real fit at assembly | — | Not yet |
| No mounts for the selected electronics | ESP32-S3-DevKitC-1, Bus Servo Adapter, distribution block, fuse holder (20 September architecture) | Fix in place as possible for the first tests | Design the mounts in | Harness bench-tested outside the chassis |
| INA219 cannot sit in the motor line | INA219 module terminal vs main cable | Voltage monitoring only; current path bypasses the shunt | Proper current sensing if wanted | I²C and voltage read confirmed; current readings invalid |

Available M4 heat-set inserts are an option for the next revision, not a validated feature of this prototype.
