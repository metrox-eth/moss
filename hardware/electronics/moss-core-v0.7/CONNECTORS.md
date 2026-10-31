# MOSS CORE V0.7 — prototype connector guide

Updated 31 October 2026: simplified motor harness, integrated 5 V converter and H1 GND connection. J2/J3/J4 have new assignments; J12/J13 are removed. See the [motor wiring guide](MOTOR_WIRING.md).

Read the numbers on the connector footprint, not the left-to-right order inferred from a top or bottom photograph. All twelve external connectors have a numbered legend on the underside. Left/right refer to the rover's forward-driving direction.

| Connector | Underside label | Connect to | Pin assignment |
|---|---|---|---|
| J1 | USB TO HUB | One downstream port of the Hoco USB hub | USB data and incoming Core logic power; use a USB data cable. |
| J20 | PI 5V OUT / POWER ONLY | Orange Pi **POWER** USB-C port | Integrated 5 V / 3 A output; no USB data. |
| J10 | BATTERY 3S | Existing fused 3S battery harness, XT30 | 1 GND/negative; 2 positive. Retain the external pack fuse. |
| J11 | CYTRON POWER | Cytron MDD10A power input | 1 switched battery positive; 2 GND. |
| J2 | CYTRON LINK | Cytron controls and four winding outputs | 1 PWM1; 2 DIR1; 3 PWM2; 4 DIR2; 5 signal GND; 6 left A; 7 left B; 8 right A; 9 right B; **10 no wire**. Supply remains on J11. |
| J3 | LEFT MOTOR | Complete left motor cable | 1 winding M1; 2 winding M2; 3 encoder GND; 4 switched 3V3; 5 encoder A; 6 encoder B. Neither winding terminal is GND. |
| J4 | RIGHT MOTOR | Complete right motor cable | Same six assignments as J3. |
| J5 | ARM | Powered arm servo daisy chain | 1 DATA; 2 switched battery positive; 3 GND. Six servos standard, seven with the optional double shoulder. |
| J7 | SPEAKER / NO GND | 4-ohm speaker | 1 amplifier positive output; 2 amplifier negative output. Both are driven: do not connect either terminal to GND. |
| J8 | STOP | Two independent normally closed contacts of the red stop button | 1/2 power-cut contact; **3/4 no wires or crimp contacts**; 5/6 status/reset contact. |
| J14 / J15 | FAN 1 / FAN 2 | Two 12 V nominal chassis fans | 1 fused 3S battery positive; 2 GND. Shared F3 1 A fuse; not regulated 12 V. |

## Grounding connection

H1, at (4, 4) mm on the PCB, is a plated 2.7 mm hole for an M2.5 screw. Its 5.4 mm exposed copper ring is connected to GND on both faces, with eight 0.5 mm stitching holes and no solder paste. It provides an attachment point for a bonding lead. The other seven mounting holes remain unplated. A screw into the plastic hull alone does not create an earth connection; ESD performance still needs testing.

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
