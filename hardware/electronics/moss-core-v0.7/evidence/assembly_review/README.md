# Assembly review following community feedback

The current board and production Gerbers were checked for solder bridges around the current-sense parts. No geometry change was needed.

| Parts | Mask and paste openings | Clear separation |
| --- | --- | --- |
| R180/R181, Bourns CSS2H-2512K-2L00F | Two 3.4 × 1.8 mm openings per shunt | 3.4 mm |
| U40/U41, TI INA240A2PWR | 0.4 × 1.475 mm, at 0.65 mm pitch | 0.25 mm |

The shunt pads match the [Bourns recommended land pattern](https://www.bourns.com/docs/Product-Datasheets/css2h-2512.pdf). The INA240 uses the correct [TI PW/TSSOP package](https://www.ti.com/lit/ds/symlink/ina240.pdf). Separate 0.18 mm Kelvin traces leave the inner edges of the appropriate shunt pads. IN+ and IN− do not share a mask or paste opening. [Exact Gerber hashes, apertures and pickup coordinates](CURRENT_SENSE_MASK_PASTE.json).

These are file-geometry checks. They do not guarantee reflow yield. PCBWay still needs to confirm stencil thickness, paste deposition and mask registration for its process.

## BOM reading view

The [classified BOM](BOM_CLASSIFIED_REVIEW.csv) separates semiconductors, passives and electromechanical parts, with readable values. It preserves all **99 MPN groups and 216 components**, including exact purchasing references, designator groups, quantities and footprints. [Comparison proof](BOM_CLASSIFICATION_PROOF.json).

PCBWay continues to receive the single grouped production CSV. Their [assembly guide](https://www.pcbway.com/smt_ordering_guide.html) asks for designators, quantities, packages and part numbers; it does not require separate active/passive files. The additional category view helps inspection without creating divergent purchasing lists. Obsolete explanatory notes in the inventory JSON were refreshed separately; the component rows and production CSV are unchanged.
