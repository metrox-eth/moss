# Harness interface verification

Updated 1 November 2026. PCB `7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14`.

## Checked evidence

The independent connector-map check matched all 76 physical connector pins across 12 connectors between PCB, schematic and circuit contract. This is a static check, not a cable or powered test. Core motor/driver housing selections are Molex 43025-0600 and 43025-1000, mating with the PCB's 43045-0612 and 43045-1012.

## Selected Micro-Fit wire and contacts

| Circuits | Wire | Contact | Installed contacts per kit |
| --- | --- | --- | --- |
| Motor winding leads | 18 AWG; tool optimum OD 1.60-1.85 mm | 43030-0038 | 8 |
| Encoder/control | 24 AWG; tool scope OD 1.42-1.85 mm | 43030-0001 | 13 |

A factory-terminated kit avoids maker crimping. For a small DIY quantity, 43030-0007 is Molex's bagged loose-piece alternative to reel 43030-0001 for 20-24 AWG. Use 63828-0200 for the listed 18 AWG / 43030-0038 combination and 63819-0000 for its listed 20-30 AWG contacts. The 18 AWG tool specifies optimal insulation OD 1.60-1.85 mm; the 20-24 AWG tool scope specifies 1.42-1.85 mm. Record the exact wire and measure insulation OD; AWG alone does not establish crimp compatibility. Thick silicone wire may not fit. Pre-crimped leads are another documented option, but verify their exact terminal, gauge, insulation and length; no specific pre-crimp lead MPN is selected here.

## Physical motor pin map remains to be recorded

Retain both six-wire pigtails supplied with Arduitronics RU00129. With power disconnected, trace each stock wire to the motor board's M1/M2, GND/VCC and C1/C2 markings. Record cavity numbers, wire gauge and insulation OD, then approve the factory wirelist. Device-end cavity numbering and OEM connector MPN are not established. Quote insulated factory transitions when the stock wire cannot be terminated directly with the specified Core contact. Never force 18 AWG into an unverified stock motor contact.

The distributor SKU identifies the supplied motor kit; it does not establish the motor connector's manufacturer or exact part number. The six-wire Core assignment is fixed; the stock device-side cavity assignment is pending continuity tracing.

## STOP

A new documented switch option is Yijia YJ-LA16-22ZS/A, red and non-illuminated, with two independent changeover contacts; use C1-NC1 and C2-NC2. An existing unmarked button can be retained only after identifying two independent NC pairs by continuity. Six tabs alone do not prove the contact arrangement. NO terminals remain unused and insulated. The 51021/51047 PicoBlade inline pair and 28 AWG OD 0.50-0.80 mm are retained.

## First article records

- Record the stock motor cavity/function map, gauge, insulation OD and factory transitions for both motors.
- Check all numbered cavities and polarity. Keep J2.10 and J8.3/4 empty.
- Record continuity and isolation of both STOP loops when released, pressed and unplugged; check isolation between loops.
- Fit the assembled loom with the cover closed and opened; verify connector seating, wire exit, bend radius, strain relief, fan clearance and HB1 excess cable storage.
- Check encoder counts/direction against an independent rotation reference during forward/reverse operation and repeated loaded reversals; inspect for resets, missed/extra counts and supply dips. This test is planned, not performed.
- Verify load, startup, temperature and voltage drop on the final wires/crimps. The driver channel rating does not establish the complete harness rating.
- Freeze the manufacturing cut/strip schedule only after these checks.

## Geometry limits

No manufacturer STEP/IGES was obtained for the cable housings. The scene uses dimensioned visual references; actual mating fit, latch operation, insertion access and cable bend remain unverified. Published current header mated height is 17.64 mm; the older family drawing reports 17.56 mm. The latter is not silently treated as the same datum. Native PCB header CAD is retained.
