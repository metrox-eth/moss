# MOSS CORE V0.7 — prototype connector guide

Read the numbers on the connector footprint, not the left-to-right order inferred from a top or bottom photograph. All fourteen external connectors have a numbered legend on the underside. Left/right refer to the rover's forward-driving direction.

| Connector | Underside label | Connect to | Pin assignment |
|---|---|---|---|
| J1 | USB TO HUB | One downstream port of the Hoco USB hub | USB data and incoming Core logic power; use a USB data cable. |
| J20 | PI 5V OUT / POWER ONLY | Orange Pi **POWER** USB-C port | 5 V output; no USB data. |
| J10 | BATTERY 3S | Existing fused 3S battery harness, XT30 | 1 GND/negative; 2 positive. Retain the external pack fuse. |
| J11 | CYTRON POWER | Cytron MDD10A power input | 1 switched battery positive; 2 GND. |
| J2 | CYTRON CTRL | Cytron control inputs | 1 PWM1; 2 DIR1; 3 PWM2; 4 DIR2; 5 GND. This order is specific to Core: check the other end of the cable. |
| J3 | ENC LEFT | Left motor encoder | 1 GND; 2 switched 3V3; 3 A; 4 B. |
| J4 | ENC RIGHT | Right motor encoder | 1 GND; 2 switched 3V3; 3 A; 4 B. |
| J12 | LEFT MOTOR LOOP | One lead between the Cytron left channel and the left motor | 1 Cytron output lead; 2 motor lead. Neither terminal is GND. |
| J13 | RIGHT MOTOR LOOP | One lead between the Cytron right channel and the right motor | 1 Cytron output lead; 2 motor lead. Neither terminal is GND. |
| J5 | ARM | Powered arm servo daisy chain | 1 DATA; 2 switched battery positive; 3 GND. Six servos standard, seven with the optional double shoulder. |
| J7 | SPEAKER / NO GND | 4-ohm speaker | 1 amplifier positive output; 2 amplifier negative output. Both are driven: do not connect either terminal to GND. |
| J8 | STOP | Two independent normally closed contacts of the red stop button | 1/2 power-cut contact; **3/4 no wires or crimp contacts**; 5/6 status/reset contact. This is the new six-position connector, not the original four-position harness. |

| J14 / J15 | FAN 1 / FAN 2 | Two 12 V nominal chassis fans | 1 fused 3S battery positive; 2 GND. Shared F3 1 A fuse; not regulated 12 V. |

## Host USB wiring

Orange Pi DATA → hub upstream. Hub downstream → Core J1, wrist camera, navigation camera and LiDAR. Core J20 → Orange Pi POWER. J1 and J20 have different roles; do not join them together. The hub's four ports are then occupied: this does not provide another free USB socket for a gamepad receiver.

## Motor-current loops

For each motor, insert its measurement loop into only one output lead:

```text
Cytron left output A  → J12.1 → onboard shunt → J12.2 → left motor lead A
Cytron left output B ─────────────────────────────────→ left motor lead B

Cytron right output A → J13.1 → onboard shunt → J13.2 → right motor lead A
Cytron right output B ────────────────────────────────→ right motor lead B
```

These are H-bridge motor leads, not battery-return terminals. The current can reverse; the reading is winding current, not total battery consumption. Confirm direction/channel naming during firmware commissioning.

## Stop-button cable

Use the matching six-position JST SH housing. Fit wires only in positions 1, 2, 5 and 6. Keep positions 3 and 4 empty and insulated from other wiring; they are not spare ground connections. Keep the cut and status circuits separate through the cable and at the switch.

- J8.1 → common of contact NC1; J8.2 → its normally closed terminal.
- J8.5 → common of independent contact NC2; J8.6 → its normally closed terminal.
- Leave the switch's normally open terminals unused and insulated. No lamp connection is provided.

The actual six-terminal button must be identified by its markings and an unpowered continuity check. Its terminal count alone does not prove the required two independent NC contacts. Empty connector positions reduce the identified adjacent-pin bridge risk; they do not make the prototype immune to arbitrary cable faults or a failed power transistor.

## Remaining qualification

J5 is one common power path for the whole arm. Its selected connector is rated 3 A per contact; the cable, aggregate load, voltage drop and temperature still require qualification for the chosen six- or seven-servo build. A seventh servo adds a bus address, not a new connector, and does not establish extra current capacity. The Core firmware must be ported and commissioned; it is not interchangeable with the former QT Py firmware.

## Chassis fans

J14 FAN 1 and J15 FAN 2: JST XH 2.50 mm, pin 1 = fused battery positive, pin 2 = GND. These are 3S battery-powered outputs (up to 12.6 V), not regulated 12 V. Two 12 V nominal fans, approximately 0.1 A each according to the user estimate; verify the actual fans. Shared F3 1 A fuse; fans remain powered during actuator stop. No PWM or tachometer. Verify actual plug and wire polarity.

## Compact input fuse

F1 is now a soldered Littelfuse 08853.15DR 3.15 A fuse on the Orange Pi power branch. The previous Schurter holder, cartridge and black cover are removed. Replacement requires soldering. F2 and F3 remain 1 A soldered branch fuses. The external 15 A battery fuse is retained.
