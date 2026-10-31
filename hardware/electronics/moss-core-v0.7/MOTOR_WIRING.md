# MOSS CORE V0.7 — motor wiring

Updated 31 October 2026. Each motor now has one six-wire cable to Core. The Cytron stays in its existing position. Its supply uses J11; its four motor outputs and four control signals share J2, with a signal-ground wire.

## Motor cables

J3 = left motor; J4 = right motor, viewed in the rover's forward-driving direction. Both have the same assignments.

| Core cavity | Function | Motor connection |
|---|---|---|
| 1 | Motor winding M1, through the corresponding current shunt | M1 |
| 2 | Motor winding M2 | M2 |
| 3 | Encoder ground | GND |
| 4 | Switched encoder supply, 3.3 V | VCC |
| 5 | Encoder channel A | C1 |
| 6 | Encoder channel B | C2 |

**Motor pins 1 and 2 are H-bridge outputs. Neither is ground.** The winding current reverses when the driver reverses. The four encoder circuits remain separate from the winding circuits.

Retain the six-way plug supplied with the Arduitronics RU00129 motor. Terminate the Core end in a Molex Micro-Fit housing. This is a function-mapped cable, not a straight-through six-pin extension: trace the stock lead to the motor board's M1/M2, GND/VCC and C1/C2 markings before terminating the first harness. Read cavity numbers from the connector drawing rather than inferring them from wire colours.

## Cytron cable

| J2 cavity | Cytron connection |
|---|---|
| 1 | PWM1 |
| 2 | DIR1 |
| 3 | PWM2 |
| 4 | DIR2 |
| 5 | Signal GND at the control header |
| 6 | Left bridge output M1A |
| 7 | Left bridge output M1B |
| 8 | Right bridge output M2A |
| 9 | Right bridge output M2B |
| 10 | Unused: no harness crimp terminal or wire |

J11 retains its separate supply: **1 = switched battery positive; 2 = GND**. The Cytron's supply current does not pass through J2's signal-ground wire. J10 is the battery XT30 input and has its own polarity marking.

The two wires of each winding stay together in the loom. Group the Cytron interconnect into one sleeved cable assembly with its J2 and J11 terminations. Each motor cable has its own sleeve and LEFT/RIGHT identification. Finished lengths need to follow the fitted routing; the earlier three-branch harness lengths are superseded.

## Connector parts

These cable-side items are separate from the PCB assembly BOM.

| Item | Quantity per rover | Manufacturer reference |
|---|---:|---|
| J3/J4 PCB headers | 2 | Molex **43045-0612**; included in PCBA BOM |
| J2 PCB header | 1 | Molex **43045-1012**; included in PCBA BOM |
| Motor cable housings, six ways | 2 | Molex **43025-0600** |
| Cytron link housing, ten ways | 1 | Molex **43025-1000** |
| Female contacts for 18 AWG winding wires | 8 | Molex **43030-0038** |
| Female contacts for 24 AWG encoder/control wires | 13 | Molex **43030-0001** |

Both contact selections require insulation OD **no greater than 1.85 mm**. Use wire that fits the specified contact; thick silicone insulation may exceed this limit. Retain the existing separately sized Cytron supply conductors and stock motor connector leads.

Manufacturer references: [six-way header](https://www.molex.com/en-us/products/part-detail/430450612), [ten-way header](https://www.molex.com/en-us/products/part-detail/430451012), [six-way housing](https://www.molex.com/en-us/products/part-detail/430250600), [ten-way housing](https://www.molex.com/en-us/products/part-detail/430251000), [18 AWG contact](https://www.molex.com/en-us/products/part-detail/430300038), [20–24 AWG contact](https://www.molex.com/en-us/products/part-detail/430300001), [populated-circuit current derating](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/430/43045/PS-43045-001.pdf).

The distributor's [RU00129 specification](https://www.arduitronics.com/product/6047/) lists the 12 V, 90:1, 110 rpm version at no more than 1 A rated current and 2.3 A stall current. These are supplier values, not measurements on MOSS. The Cytron's 10 A channel specification is not the current rating of the complete Core/harness assembly. Actual load, startup, temperature and wire/crimp performance remain prototype bench checks.
