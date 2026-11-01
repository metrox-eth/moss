# MOSS CORE V0.7 — prototype connector guide

Updated 1 November 2026: black solder mask, large white connector-function labels on the underside, fan headers shifted left and the speaker header retained on the right. The outline is a rounded 82 × 79 mm rectangle without protruding ears. The integrated 5 V converter, consolidated motor cables and H1 GND connection are retained. See the [motor wiring guide](MOTOR_WIRING.md).

Read the numbers on the connector footprint, not the left-to-right order inferred from a top or bottom photograph. All twelve external connectors have a numbered legend on the underside. Left/right refer to the rover's forward-driving direction.

| Connector | Underside label | Connect to | Pin assignment |
|---|---|---|---|
| J1 | USB Data | One downstream port of the Hoco USB hub | USB data and incoming Core logic power; use a USB data cable. |
| J20 | USB Power Out | Orange Pi **POWER** USB-C port | Integrated 5 V / 3 A output; no USB data. |
| J10 | Battery In / 3S / 12 V | Existing fused 3S battery harness, XT30 | 1 GND/negative; 2 positive. A charged 3S pack reaches 12.6 V. Retain the external pack fuse. |
| J11 | Motor Driver Power | Cytron MDD10A power input | 1 switched battery positive; 2 GND. |
| J2 | Motor Driver | Cytron controls and four winding outputs | 1 PWM1; 2 DIR1; 3 PWM2; 4 DIR2; 5 signal GND; 6 left A; 7 left B; 8 right A; 9 right B; **10 no wire**. Supply remains on J11. |
| J3 | Left Motor | Complete left motor cable | 1 winding M1; 2 winding M2; 3 encoder GND; 4 switched 3V3; 5 encoder A; 6 encoder B. Neither winding terminal is GND. |
| J4 | Right Motor | Complete right motor cable | Same six assignments as J3. |
| J5 | Arm Servos | Powered arm servo daisy chain | 1 DATA; 2 switched battery positive; 3 GND. Six servos standard, seven with the optional double shoulder. |
| J7 | Speaker | 4-ohm speaker | 1 amplifier positive output; 2 amplifier negative output. Both are driven: do not connect either terminal to GND. |
| J8 | Stop | Two independent normally closed contacts of the red stop button | 1/2 power-cut contact; **3/4 no wires or crimp contacts**; 5/6 status/reset contact. |
| J14 / J15 | Fan 1 / Fan 2 | Two 12 V nominal chassis fans | 1 fused 3S battery positive; 2 GND. Shared F3 1 A fuse; not regulated 12 V. |

## Vertical cable headers

Battery J10 uses **AMASS XT30UPB-M.G.Y** (5.00 mm pin pitch), servo bus J5 uses **Molex 22-03-5035 / 5267-03A** (2.50 mm), and speaker J7 uses **JST B2B-PH-K-S(LF)(SN)** (2.00 mm). Their cable mates insert from above the PCB. J5 is intended for the 5264-family cable housing; J7 retains the PHR-2 housing. Use the new footprints and purchasing list together: the former horizontal headers are not substitutes.

With the Orange Pi on 20 mm standoffs, route the J2 driver bundle rearward and the J3 left-motor bundle leftward, away from the Orange Pi, before turning upward. Do not force either bundle vertically against the SBC. See the [combined assembly check](evidence/MECHANICAL_REVIEW.json).

The motor/driver Micro-Fit headers, fan headers and stop header are also top-entry. The two USB-C sockets remain side-entry. The Orange Pi mounting checks include header bodies, mating-plug envelopes and reserved wire-exit space; the exact seating, cable bend and assembly access still need a physical prototype check.

Manufacturer references: [AMASS XT30UPB-M](https://www.china-amass.net/xt30upb-m-product/), [Molex 22-03-5035](https://www.molex.com/en-us/products/part-detail/22035035), [JST PH series](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf).

**J5 connector identification:** Feetech specifies **5264-3P** for [STS3215](https://files.seeedstudio.com/products/Feetech/108090023_STS3215-C001_Datasheet.pdf#page=4) and [STS3235](https://pages.switch-science.com/comparison/files/feetech/serial-sts/STS3235_datasheet.pdf#page=4). The [Molex 5267 drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/526/5267/022035025_sd.pdf) includes 22035035/526703A and identifies 5264N as the mating housing. The family choice is documented, but Feetech does not identify an exact Molex housing MPN; fit and cable pin orientation must be confirmed with the supplied servo cable. The rendered J5 model is a dimensioned visual reconstruction with simplified small locking features, not manufacturer mating CAD. Missing fine notches in that model are not evidence of the actual ordered part's profile.


## Grounding connection

The four Core chassis fixings now use a **74 × 71 mm** pattern, with centres 4 mm from the enlarged board edges. The hull mounting posts need adapting to this new pattern. The four Orange Pi mounting holes are unchanged. See [mounting dimensions](MOUNTING.md).

H1, at native KiCad coordinates (2, 0) mm on the PCB, is a plated 2.7 mm hole for an M2.5 screw. Its 5.4 mm exposed copper ring is connected to GND on both faces, with eight 0.5 mm stitching holes and no solder paste. It provides an attachment point for a bonding lead. The other seven mounting holes remain unplated. A screw into the plastic hull alone does not create an earth connection; ESD performance still needs testing.

White silkscreen rings identify the other mounting positions on both faces: thick rings for the Core mounting screws H2–H4, and compact rings for the Orange Pi standoffs H5–H8. The Core fixing markers retain a 5.4 mm outer diameter. The Orange Pi rings have a 4.2 mm outer diameter, 3.0 mm inner diameter and 0.6 mm ink width, leaving 0.15 mm around each hole. These are printed assembly guides; the seven holes retain their existing unplated 2.7 mm drills.

## Host USB wiring

Orange Pi DATA → hub upstream. Hub downstream → Core J1, wrist camera, navigation camera and LiDAR. Core J20 → Orange Pi POWER. J1 and J20 have different roles; do not join them together. The hub's four ports are then occupied: this does not provide another free USB socket for a gamepad receiver.

## Motor-current loops

The current shunts remain on Core. Their connections are now carried by the consolidated motor ports:

```text
Cytron M1A → J2.6 → left shunt  → J3.1 → left winding M1
Cytron M1B → J2.7 ─────────────→ J3.2 → left winding M2
Cytron M2A → J2.8 → right shunt → J4.1 → right winding M1
Cytron M2B → J2.9 ─────────────→ J4.2 → right winding M2
```

Both winding legs are H-bridge outputs. The nets named `MOTOR_L_RETURN` and `MOTOR_R_RETURN` are the second winding leads, not ground returns. The measurement remains bidirectional winding current, not total battery consumption. Confirm direction/channel naming during firmware commissioning.

## Stop-button cable

Use the matching six-position JST SH housing. Fit wires only in positions 1, 2, 5 and 6. Keep positions 3 and 4 empty and insulated from other wiring; they are not spare ground connections. Keep the cut and status circuits separate through the cable and at the switch.

- J8.1 → common of contact NC1; J8.2 → its normally closed terminal.
- J8.5 → common of independent contact NC2; J8.6 → its normally closed terminal.
- Leave the switch's normally open terminals unused and insulated. No lamp connection is provided.

The actual six-terminal button must be identified by its markings and an unpowered continuity check. Its terminal count alone does not prove the required two independent NC contacts. Empty connector positions reduce the identified adjacent-pin bridge risk; they do not make the prototype immune to arbitrary cable faults or a failed power transistor.

## Remaining qualification

J5 is one common power path for the whole arm. Its selected connector is rated 3 A per contact; the cable, aggregate load, voltage drop and temperature still require qualification for the chosen six- or seven-servo build. A seventh servo adds a bus address, not a new connector, and does not establish extra current capacity. The Core firmware must be ported and commissioned; it is not interchangeable with the former QT Py firmware.

## Chassis fans

J14 FAN 1 and J15 FAN 2: JST XH 2.50 mm, pin 1 = fused battery positive, pin 2 = GND. These are 3S battery-powered outputs (up to 12.6 V), not regulated 12 V. The two 12 V nominal fans are estimated at 0.1 A each; their current has not been measured. Shared F3 1 A fuse; fans remain powered during actuator stop. No PWM or tachometer. Verify actual plug and wire polarity.

## Compact input fuse

F1 is a soldered Littelfuse 08853.15DR 3.15 A fuse on the battery input to the integrated Orange Pi converter. There is no separate holder or cover. Replacement requires soldering. F2 and F3 remain 1 A soldered branch fuses. The external 15 A battery fuse is retained.
