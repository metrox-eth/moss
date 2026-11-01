# Geometry sources and limits

| Item | Source / status |
| --- | --- |
| MOSS Core PCB | Fresh native KiCad export of PCB SHA256 `7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14`, 82 x 79 mm. [Export record](data/CURRENT_CORE_PROVENANCE.json). Fixed headers, components and copper are native source geometry. The renderer displays the intended black PCB mask. |
| Orange Pi | Supplied Orange Pi Zero 3W STEP, all native occurrence transforms retained, in the previously confirmed orientation. The cooling illustration fits within the measured 16 mm board/cooler assembly height. Standoffs are a 20 mm CAD assumption, not a newly measured height. |
| Core Micro-Fit cable mates | Dimensioned MOSS reconstruction of 43025-0600 / 43025-1000. Manufacturer drawing 430250000-SD: body length 9.85 / 15.85 mm, axial length 14 mm, across-body 6.85 mm, pitch 3 mm. Published current header mated height 17.64 mm is used as a reservation; exact seat plane, latch and cavity clocking are not vendor-CAD-qualified. Fixed headers remain native KiCad models. |
| Other cable housings | Public JST SH/PH/XH, Molex SPOX and AMASS dimensions; reconstructed cavity/latch references. Vertical J5/J7/J10 follow the current native headers. Not manufacturer mating CAD. |
| Motors and encoder boards | Existing placed MOSS geometry. The six-way motor interface is an XH-style visual reference from the workshop/product photos; retain the supplied Arduitronics RU00129 pigtail. OEM connector identity and physical cavity order are not established by the model. |
| Cytron MDD10A | Existing detailed visual reference, with controls and winding-output terminals in their existing positions. J2 has nine active wires; the separate J11 cable supplies power. |
| Hoco HB1 | Photo-based model: 78 x 25 x 25 mm published envelope. Ports follow the official photo; fillets/caps are illustrative. Hub/cradle are shifted 10 mm toward +Y in this packaging proposal. Its 800 mm captive lead is not fully coiled. |
| Speaker | Original R92 Speaker_3W_4Ohm geometry, re-tessellated without moving it. Cable outlet is a reserved lead position. |
| Fans / battery / STOP | Fans are 30 x 30 x 10 mm references; lead corners are reserved. Battery is the measured 140 x 73 x 48 mm envelope with a proposed outlet. STOP keeps the R92 pose. PicoBlade 51021/51047 disconnect uses the published 9 mm mated length and 1.25 mm pitch. |
| Hull and ties | Updated native prototype with 74 x 71 mm Core boss pattern, five integral bridges and the existing divider notch. Same R92 frame, millimetres. See the independent hull evidence and mechanical folder. |

The current wire model uses 18 AWG winding wires at 1.8 mm OD and 24 AWG signals at 1.5 mm OD. Straight bundle packing is non-overlapping; supplier wire/insulation and complete crimp/sleeve dimensions must be fixed on the first article. Colours and the stock motor cavity order in the picture are illustrative, not a wirelist.

## Dimensional references

- [Molex Micro-Fit 430250000-SD family drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43025/430251600_sd.pdf)
- [Six-way header 43045-0612](https://www.molex.com/en-us/products/part-detail/430450612), [ten-way header 43045-1012](https://www.molex.com/en-us/products/part-detail/430451012)
- [JST SH](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf), [PH](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf), [XH](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf)
- [Molex SPOX housing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/526/5264/050375023_sd.pdf)
- [Molex PicoBlade mating drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/510/51047/510470400_sd.pdf)
- [HOCO HB1 dimensions](https://hocotech.com/product/mobile-accessories/cables/hubs-organizers/usb-hub-hb1-four-ports-usb-2-0-charging-and-data-sync/), [official port photo](https://hocotech.com/wp-content/uploads/2018/07/hb1-four-usb-hub-silver-ports.jpg)

[Connector placements](data/CONNECTOR_PLACEMENT.json), [model scope](data/MODEL_SCOPE.json), [HB1 record](data/HOCO_PROVENANCE.json), [speaker record](data/SPEAKER_PROVENANCE.json).
