# Hardware

The current mechanical package is [V0.6 / R92](https://github.com/metrox-eth/moss/releases/tag/v0.6-r92). [Download CAD, STL & 3MF](https://github.com/metrox-eth/moss/releases/download/v0.6-r92/MOSS_R92_Mechanical_20261024.zip) · [Build guide](https://www.showrobotics.ai/moss/build/). It contains individual STL files, editable Fusion source, STEP solid geometry, per-part revisions and attribution. Third-party electronics reference models remain in the internal integration assembly.

See the [print catalogue](../3DPrinting.md), [BOM](../BOM.md) and [assembly guide](../Assembly.md). Choose the one-piece hull or the current R92 two-piece alternative. The two-piece native Fusion sources are supplied separately from the main one-piece CAD set.

`bench/` retains the raw bench traces. The 20 September INA219 trace is not a motor-current measurement.

## Custom battery

[3S4P battery build tutorial](power/custom-3s4p-battery/) — parts, photographs, wiring and assembly for the twelve-cell EVE 21700 pack, with a 15 A blade fuse, 12 AWG main leads and 14 AWG inline fuse-holder pigtails. The updated parts list specifies 130 mm heat-shrink and fishpaper. Rated 20 Ah from the cell specifications; assembled mass 910 g. Actual capacity and collection runtime still need measuring. Read the workshop disclaimer before considering this build.

## Electronics prototypes

[MOSS CORE V0.7 — Prototype](electronics/moss-core-v0.7/) is the single current community design review: editable KiCad files, component views, grouped BOM, connector guide, Gerbers and static review evidence. **Updated 31 October 2026:** the Orange Pi converter is now integrated, H1 provides a GND connection, and manufacturing-review corrections are included. Per-motor current sensing, fan outputs and the compact host-branch fuse remain. **Not fabricated yet: not production-ready or hardware-qualified.** Electrical, connector and real-load review is welcome. Hardware revision letters are reserved for fabricated iterations.

[MOSS Core V1D](electronics/moss-core-v1d/) is retained as the previous routed design review. Its assumptions and package are historical; it is not the current V0.7 design.

[V1C](electronics/moss-core-v1c/) is retained for traceability and **must not be fabricated** because of a physical-pin mapping error; see the [critical erratum](electronics/moss-core-v1d/V1C_CRITICAL_ERRATA.txt).
