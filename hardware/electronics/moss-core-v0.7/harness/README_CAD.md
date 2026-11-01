# MOSS CORE V0.7 - current harness study

Updated 1 November 2026 for PCB `7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14`.

The current model has **14 routed paths**, including complete six-wire left/right motor cables, a nine-wire driver link, the separate two-wire driver supply, two STOP halves, optional arm/speaker/fan adapters and three complete USB cable assemblies. The custom route schedule contains 42 wire segments; the three USB assemblies are counted as cables, not as individual USB conductors.

Supply H02 and nine-wire H03 form one sleeved Cytron cable ensemble with TWO Core terminations: J11 for supply and J2 for controls plus four winding outputs. H03 has no supply-positive conductor. J2.5 is signal ground; driver supply current uses J11. Leave J2.10 empty. Neither winding lead is ground.

## Current review files

- MOSS_HARNESS_VIEWER.html: self-contained offline viewer.
- MOSS_HARNESS_ASSEMBLY.glb and MOSS_HARNESS_ONLY.glb: meshes for the current scene.
- ROUTE_LENGTHS.json: current modelled route/conductor lengths and assumptions.
- rfq/MOSS_CORE_V07_HARNESS_RFQ.pdf: dated prototype quotation package.
- rfq/HARNESS_SPECIFICATION.json and rfq/WIRELIST.csv: same functional wiring schedule.
- CONNECTIONS.md and INTERFACE_VERIFICATION.md: wiring and first-article requirements.

Only the STOP tail follows the removable lid. The arm route remains with the chassis. Sleeve sizes, tie access, retained motor pigtails and complete USB lead storage still need physical fit checks. Any historical film is superseded for this revision; use the current viewer and dated RFQ.

## Lengths

CAD lengths follow the relaxed connector wire-exit to wire-exit paths, including the service slack drawn. Prototype quote free span = longest modelled conductor + 20 mm, rounded up to 5 mm; target tolerance +/-5 mm. The assembler adds cut/strip, contact engagement and termination allowances. These are quotation estimates, not released cut lengths. Fit the first article before freezing the batch. Complete USB cables are selected commercially and are not cut to CAD length.

H03's centreline measures the common trunk only; its individual conductor lengths include the fan-out. Use the individual wire lengths for the prototype span calculation.

| Route | Function | Wires / cable | CAD centreline mm | Quote free span mm |
| --- | --- | --- | --- | --- |
| H01 | Battery supply | 2 | 162.4 | 185 |
| H02 | Cytron supply | 2 | 119.0 | 145 |
| H03 | Cytron combined link | 9 | 85.4 | 260 |
| H04 | Left motor and encoder | 6 | 50.4 | 80 |
| H05 | Right motor and encoder | 6 | 119.4 | 150 |
| H08_chassis | STOP / chassis half | 4 | 125.9 | 150 |
| H08_lid | STOP / removable lid tail | 4 | 111.6 | 135 |
| O01 | Arm bus input | 3 | 239.6 | 265 |
| O02 | Speaker lead | 2 | 65.9 | 90 |
| O03_left | Fan 1 / left cooling fan | 2 | 206.2 | 230 |
| O03_right | Fan 2 / right cooling fan | 2 | 131.4 | 155 |
| U01 | Orange Pi POWER | 1 | 90.7 | Complete cable |
| U02 | Core USB data | 1 | 136.9 | Complete cable |
| U03 | Hub upstream / Pi DATA | 1 | 207.8 | Complete cable |

## Visible wire and sleeve dimensions

The model shows 18 AWG winding wires at OD 1.8 mm and 24 AWG control/encoder wires at OD 1.5 mm. H03's common-trunk sleeve envelope is about 7.1 mm OD and its four-output power-branch sleeve is 5.3 mm OD; each complete six-wire motor sleeve is about 6.1 mm OD. These are visual routing dimensions; supplier wire and sleeve dimensions require prototype confirmation. The selected hand-tool processes specify wire insulation OD 1.60-1.85 mm for 18 AWG and 1.42-1.85 mm for 24 AWG.

## Connector and workmanship limits

Retain both six-wire pigtails supplied with Arduitronics RU00129. With power disconnected, trace each stock wire to the motor board's M1/M2, GND/VCC and C1/C2 markings. Record cavity numbers, wire gauge and insulation OD, then approve the factory wirelist. Device-end cavity numbering and OEM connector MPN are not established. Quote insulated factory transitions when the stock wire cannot be terminated directly with the specified Core contact. Never force 18 AWG into an unverified stock motor contact.

A factory-terminated kit avoids maker crimping. For a small DIY quantity, 43030-0007 is Molex's bagged loose-piece alternative to reel 43030-0001 for 20-24 AWG. Use 63828-0200 for the listed 18 AWG / 43030-0038 combination and 63819-0000 for its listed 20-30 AWG contacts. The 18 AWG tool specifies optimal insulation OD 1.60-1.85 mm; the 20-24 AWG tool scope specifies 1.42-1.85 mm. Record the exact wire and measure insulation OD; AWG alone does not establish crimp compatibility. Thick silicone wire may not fit. Pre-crimped leads are another documented option, but verify their exact terminal, gauge, insulation and length; no specific pre-crimp lead MPN is selected here.

The mesh display's colours and wire order are illustrations. Read cavity numbering from the exact connector drawing and continuity-check the stock device leads. This study does not claim completed physical qualification or manufacturer cable-housing CAD.
