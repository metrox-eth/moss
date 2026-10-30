# Harness interface verification

Checked 31 October 2026 against the current Core circuit and supplier documentation. This record distinguishes catalogue evidence from checks on the physical rover.

## Motors

The matching distributor listing is **Arduitronics RU00129**, JGB37-520 encoder motor kit, 12 V / 110 rpm. Its specification image lists a 90:1 reduction. The kit includes the six-wire motor cable. [Product and original photographs](https://www.arduitronics.com/product/6047/).

The close-up of the encoder board shows the labels **M1, GND, C2, C1, VCC, M2**. M1/M2 are motor terminals; VCC/GND power the encoder; C1/C2 are its two signal channels. The photographed connector and encoder PCB agree visually with the MOSS workshop photograph. A photo does not establish the connector manufacturer's part number or pitch tolerance.

**Procurement choice:** retain the cable supplied with RU00129 and terminate its other end as part of the loom. Do not substitute a generic PH/XH six-pin connector by appearance. The motor plug in the model remains an XH-style visual reference. Before terminating the first kit, trace the stock pigtail to the board's function labels and record its cavity numbering, wire gauge and insulation diameter. Apply the resulting schedule to both motor branches. This is a continuity check, with the motor unpowered.

ASLONG / Shenzhen Jinshunlaite manufactures a [JGB37-520B family](https://www.aslongdcmotor.com/sale-45027788-12v-dc-motor-encoder-jgb37-520b-37mm-brush-motor-12v-volt-brushed-gear.html), but no source found connects Arduitronics RU00129 to that factory. The RFQ identifies the distributor SKU without assigning an unverified OEM.

## STOP button

The [Yijia LA16 catalogue](https://yijiabutton.com/wp-content/uploads/2023/10/28.-YJ-LA16-Specification.pdf) distinguishes **11 = one changeover contact** from **22 = two independent changeover contacts**. Core requires two normally closed loops. For a new, factory-wired prototype, the documented reference is **YJ-LA16-22ZS/A**, red, non-illuminated, 16 mm mounting hole, 30 mm head. Its tabs are 2.8 x 0.5 mm. Quote the smaller-head **22ZS** only as a declared alternative.

Use C1-NC1 for CUT and C2-NC2 for STATUS. Both loops are closed when released and open when pressed. NO1/NO2 remain unused. J8 uses cavities **1, 2, 5, 6**; 3/4 have no contacts. The existing unmarked button is not identified as a Yijia part. It can be reused after identifying its two independent NC pairs by continuity. Six terminals alone do not establish that arrangement.

The older rover BOM names LA16-11ZS/A; that is not an adequate purchasing specification for Core's two-loop input. This V0.7 specification supersedes it for the Core harness, without silently changing the released V0.6 build.

## Lid disconnect

The initial Micro-Fit proposal was removed. [Molex tooling data](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/applicationtoolingspecificationpdf/638/63819/ATS-638190000-001.pdf) specifies 1.09-1.27 mm insulation for the selected contacts, outside the 0.40-0.80 mm range at the Core JST SH connector.

The replacement uses **PicoBlade 51021-0400 + 51047-0400**, with **50058-8000 female + 50133-8000 male contacts**. Both terminal types accept 28 AWG and 0.50-1.00 mm insulation. Specifying **28 AWG, insulation OD 0.50-0.80 mm including tolerance**, is compatible with both PicoBlade and JST SH. The two halves use the same circuit numbers 1-4. This is a polarized friction-retained connector, not a lever-release latch. Hold the housings when disconnecting and secure the nearby loom so the lid does not pull on it.

Sources: [mating drawing, page 2](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/510/51047/510470400_sd.pdf), [female contact](https://www.molex.com/en-us/products/part-detail/500588000), [male contact](https://www.molex.com/en-us/products/part-detail/501338000), [JST SH](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf).

## First article

Before releasing more than the prototype kits: record the motor pigtail map; test both STOP loops; check connector fit and polarity; fit the loom with the cover closed and open. Store the HB1's excess captive cable outside the fans and moving parts. Only then freeze finished cable lengths and the factory cut/strip schedule. No physical test result is claimed by this repository.
