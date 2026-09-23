# Assembly feedback — V0.3 prototype

One line per finding: what was observed, which part and revision, what was done on the prototype, what is planned for the next revision, and what validation actually happened. The first physical drive happened on 22 September; each row below distinguishes that observation from unvalidated V0.4 changes.

| Finding | Part / revision | On the prototype | Next revision | Validation done |
|---|---|---|---|---|
| TPU track too stiff | Track printed with a 0.8 mm nozzle | Not used; the 0.4 mm profile (nozzle, extrusion width, walls, layer height, infill, material) is the reference | Record the full print profile with the part | 0.4 mm track: manual floor test, good flexibility and grip |
| Motor mounts | Corrected brackets Ø31 / M3 (files marked V2-01) | Check screw depth at assembly | — | Not yet |
| Motor mount to hull joint | Interior access is difficult | Head recesses / through access drilled on the prototype | Exterior-access recessed M4 heads and captive nuts in the motor support; standard M4 × 20 in the CAD study | Local CAD checks; complete printed joint and tool access still to validate |
| Front of the cover and offset arm plate | Cover, arm plate | Keep the unfinished interface as is | Complete-cover study, parked | — |
| Camera brackets | Two RealSense D455 brackets | Fit at assembly | — | Not yet |
| Plate gasket | R8 gasket listed with the R11 plate | Check the real fit at assembly | — | Not yet |
| Track tension uneven | Single-sided tensioner per track | Live with some slack for the first drives | Second tensioner on each track | First drive, 22 September: rolls, slack visible |
| No mounts for the selected electronics | ESP32-S3-DevKitC-1, Bus Servo Adapter, distribution block, fuse holder (20 September architecture) | Fix in place as possible for the first tests | Design the mounts in | Harness bench-tested outside the chassis |
| INA219 cannot sit in the motor line | INA219 module terminal vs main cable | Voltage monitoring only; current path bypasses the shunt | Proper current sensing if wanted | I²C and voltage read confirmed; current readings invalid |

Available M4 heat-set inserts are an option for the next revision, not a validated feature of this prototype.

## V0.4 follow-up — 24 September

| Finding / request | V0.4 response | Status |
|---|---|---|
| Jetson caddy and cables do not fit | Integrated seat for the original plastic base, retainers and USB-side cable route | Current hull CAD; printed fit pending |
| Individual Dupont connections are inconvenient | QT Py ESP32-S3 with screw-terminal BFF and STEMMA QT INA connection | Two sets ordered; wiring and firmware migration pending |
| Two MD10Cs take more space than needed | One Cytron MDD3A dual driver | Ordered earlier, selected for CAD; rover validation pending |
| RealSense straight USB plug lacks clearance | Ordered right-angle USB3 cable; housing reserve | Cable dimensions and USB3 stability untested |
| INA connector access | Existing module model and fixings rotated 90 degrees | Approximate existing-board CAD; new Adafruit footprint not yet reconciled |
| Battery installation under arm | Current pack 67 × 74 × 27 mm; larger 75 × 82 × 32 mm candidate envelope | Envelope only; detachable lower platform deferred |
| Bin retention | Four 40 × 10 × 5 mm magnets | Ordered; mounting design pending |
| Wheel / roller screws protrude | Recess the screw heads | Requested; not claimed implemented |
| Hard-to-source screw lengths | Standard readily available lengths, without custom cutting | Design rule; full fastener audit pending |
| Tracks may be too long | Test maximum adjustment and candidate one-tooth shortening | Hypothesis; no validated new belt length |
| Separate fuse mount takes space | Inline fuse holder on a cable | Selected arrangement; final full-robot rating not established |

Keep the corrected flank geometry. Do not move the fourth fixing solely because of the initial wrong-rail tensioner placement. See [the complete V0.4 status](hardware_v04.md).
