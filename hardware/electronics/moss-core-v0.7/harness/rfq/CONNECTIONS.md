# Where the cables go

Updated 1 November 2026 for PCB `7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14`. Twelve external PCB connectors; fourteen routed paths.

J3 is the complete left motor cable and J4 is the complete right motor cable, viewed in the rover's forward-driving direction. Each has six wires.

Supply H02 and nine-wire H03 form one sleeved Cytron cable ensemble with TWO Core terminations: J11 for supply and J2 for controls plus four winding outputs. H03 has no supply-positive conductor. J2.5 is signal ground; driver supply current uses J11. Leave J2.10 empty. Neither winding lead is ground.

| Core connector | Numbered cavities |
| --- | --- |
| J10 | 1 BAT_NEG (GND); 2 BAT_POS (BAT_PROTECTED) |
| J11 | 1 CYTRON_BAT_POS (ACTUATOR_SW); 2 MOTOR_NEG (GND) |
| J2 | 1 PWM1 (MDD_PWM1); 2 DIR1 (MDD_DIR1); 3 PWM2 (MDD_PWM2); 4 DIR2 (MDD_DIR2); 5 SIGNAL_GND (GND); 6 LEFT_A (CYTRON_L_LEAD); 7 LEFT_B (MOTOR_L_RETURN); 8 RIGHT_A (CYTRON_R_LEAD); 9 RIGHT_B (MOTOR_R_RETURN); 10 UNUSED (NO WIRE) |
| J3 | 1 M1 (MOTOR_L_LEAD); 2 M2 (MOTOR_L_RETURN); 3 ENC_GND (GND); 4 ENC_3V3 (ENC_3V3); 5 ENC_A (EL_A_EXT); 6 ENC_B (EL_B_EXT) |
| J4 | 1 M1 (MOTOR_R_LEAD); 2 M2 (MOTOR_R_RETURN); 3 ENC_GND (GND); 4 ENC_3V3 (ENC_3V3); 5 ENC_A (ER_A_EXT); 6 ENC_B (ER_B_EXT) |
| J5 | 1 DATA (SERVO_BUS); 2 V_SERVO_3S (ACTUATOR_SW); 3 GND (GND) |
| J7 | 1 SPK_P (SPEAKER_P); 2 SPK_N (SPEAKER_N) |
| J8 | 1 CUT_SOURCE (ESTOP_CUT_SOURCE); 2 CUT_RETURN (ESTOP_CUT_RETURN); 3 DNC_3 (NO WIRE); 4 DNC_4 (NO WIRE); 5 STATUS_SOURCE (ESTOP_STATUS_SOURCE); 6 STATUS_RETURN (ESTOP_STATUS_RAW) |
| J14 | 1 FAN_POS (FAN_3S); 2 FAN_NEG (GND) |
| J15 | 1 FAN_POS (FAN_3S); 2 FAN_NEG (GND) |

## USB

U01: Core J20 to Orange Pi POWER, complete C-to-C 5 V/3 A cable. U02: HB1 downstream to Core J1, complete A-to-C data cable. U03: Orange Pi DATA through a USB-C OTG adapter to the HB1 captive USB-A upstream lead. Hub downstream sockets serve Core, wrist camera, navigation camera and LiDAR. The HB1 has an 800 mm captive lead; only the routed portion is modelled. Store excess cable clear of fans and moving parts.

## STOP and lid disconnect

J8.1/2 connect to C1/NC1 and J8.5/6 to C2/NC2. Cavities 3 and 4 remain empty, with no contacts or wires. X08 is PicoBlade 51021-0400/51047-0400 with 50058-8000/50133-8000 contacts. Map J8.1/2/5/6 to X08 circuits 1/2/3/4, straight through. Use 28 AWG with insulation OD 0.50-0.80 mm. The connector is friction-retained; hold both housings when disconnecting. Only the STOP tail moves with the lid.

## Motor device ends

Retain both six-wire pigtails supplied with Arduitronics RU00129. With power disconnected, trace each stock wire to the motor board's M1/M2, GND/VCC and C1/C2 markings. Record cavity numbers, wire gauge and insulation OD, then approve the factory wirelist. Device-end cavity numbering and OEM connector MPN are not established. Quote insulated factory transitions when the stock wire cannot be terminated directly with the specified Core contact. Never force 18 AWG into an unverified stock motor contact.

The current shunts remain on Core: Cytron M1A -> J2.6 -> left shunt -> J3.1; M1B -> J2.7 -> J3.2. Right side: M2A -> J2.8 -> right shunt -> J4.1; M2B -> J2.9 -> J4.2. J3/J4.3 is encoder GND, .4 is switched 3.3 V, .5 channel A/C1 and .6 channel B/C2. Neither .1 nor .2 is ground.

Speaker J7 has two driven amplifier outputs. Fans J14/J15 use fused 3S battery positive and GND, up to 12.6 V; they are not regulated 12 V outputs. J5 is one bus for the whole arm, not one connector per servo.
