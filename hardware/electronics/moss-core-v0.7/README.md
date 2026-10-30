# MOSS CORE V0.7 — Rev D community review

This is my first custom PCB for **MOSS, the litter-picking rover**, designed with Codex and KiCad. I am publishing the editable design so people with electronics experience can help review it before the first assembled prototypes are tested.

**Untested prototype — not a production-ready or hardware-qualified design.** The files are suitable for design/manufacturing review; passing the recorded ERC/DRC does not establish that the powered board works safely or reliably.

![MOSS CORE V0.7 Rev D, component side](preview/BOARD_TOP.png)

![MOSS CORE V0.7 Rev D, underside](preview/BOARD_BOTTOM.png)

## What the board does

The 80 × 75 mm, four-layer board combines an ESP32-S3 controller, a powered half-duplex serial-servo interface, Cytron control and encoder interfaces, left/right motor-current sensing, battery-voltage measurement, an I2S speaker amplifier and an Orange Pi power supply based on a soldered Waveshare module. The Cytron motor driver and USB hub remain external.

The arm uses one daisy-chain connector for the standard six-servo configuration, or seven with the optional twin shoulder. The selected connector and the actual common power harness still need aggregate-current qualification. The Core firmware needs its own port and commissioning; this is not a drop-in replacement for the existing controller firmware.

## Changes in Rev D

- Two chassis-fan outputs, J14/J15, with JST XH 2.50 mm headers and a shared 1 A branch fuse. These carry fused 3S battery voltage, up to 12.6 V, rather than regulated 12 V. The two fans' combined 0.2 A running current is an estimate, not a measurement.
- Corrected connector legends, including the underside servo pin order. The stop connector J8 now has six positions, with 3/4 deliberately unwired to separate the cut and status circuits.
- A compact soldered **Littelfuse 08853.15DR, 3.15 A**, replaces the separate cartridge, holder and cover on the Orange Pi supply branch. It is not the servo/motor fuse, and replacement requires soldering. The existing external 15 A battery fuse remains required.
- A larger MOSS CORE V0.7 wordmark in the recovered space, with nearby traces rerouted to clear the new fuse lands.

See the [connector guide](CONNECTORS.md) and [F1 selection evidence](review/F1_SELECTION.md).

## Open the design

- [KiCad project](kicad/MOSS_Core_V07_DRAFT.kicad_pro), [PCB](kicad/MOSS_Core_V07_DRAFT.kicad_pcb) and [root schematic](kicad/MOSS_Core_V07_DRAFT.kicad_sch).
- [Physical-pin circuit contract](kicad/circuit.json), local symbols and footprints in `kicad/`.
- [Grouped component BOM](manufacturing/BOM_REV_D.csv) and [placement file](manufacturing/POSITIONS_REV_D.csv): 194 placed components, 89 purchase articles. The native board also contains mounting holes and test pads, for 208 footprints total.
- [Gerbers and drill files](manufacturing/MOSS_CORE_V07_REV_D_GERBERS_20261030.zip), exported from this exact board for review.
- [File hashes](MANIFEST.json) and [publication notes](review/PUBLICATION_NOTES.json).

Use KiCad 10. Open the project from the `kicad/` directory so `${KIPRJMOD}` resolves its local libraries and models. All 44 model files referenced by the native PCB are included. Some footprint-library defaults still reference KiCad's installed model library; preserve the reviewed native-board model overrides. Several custom models are dimensioned visual approximations, not manufacturer mating CAD.

The PCB bytes are unchanged from the checked Rev D snapshot:

```text
SHA-256: 3fdbd54e1b858c0d1bfd9ce2af361dc4c660273fec9b26b3768d296a7c1e1fe8
```

## Checks and questions for reviewers

The recorded [ERC](review/ERC_FINAL.json) has zero violations. The [PCB DRC](review/DRC_FINAL.json), under the saved project rules, has zero errors, zero missing connections and zero schematic-parity issues. Two pre-existing locked dangling-track warnings remain on `PWM_L` and `BAT_PROTECTED`.

I would especially welcome review of:

- Exact component/pin/footprint matching and connector mating/polarity.
- Power distribution, conductor widths, return paths, decoupling and the routing choices, including the unusual-looking trace angles.
- Host-supply startup and voltage margin, fuse/conductor coordination, thermal behavior and realistic hub/peripheral loads.
- The shared servo connector/harness current, actuator-cutoff behavior and motor regeneration/BMS interactions.

These are open design and bench-validation topics. The fan connector identity/current and stop-button contact arrangement also need physical confirmation. No firmware or real-load test result is implied by the 3D views or static checks.

Please [open an issue](https://github.com/metrox-eth/moss/issues) with **MOSS CORE V0.7 Rev D**, the component/net reference, and the relevant datasheet or calculation. Corrections and practical suggestions are very welcome.

## License and provenance

MOSS hardware design: [CERN-OHL-S-2.0](../../../LICENSE-HARDWARE). Documentation/media: CC BY 4.0, as described in the repository [NOTICE](../../../NOTICE). Bundled KiCad library material retains its [upstream license and exception](KiCad_Libraries_LICENSE.md).

Only the current technical design, referenced models, manufacturing-review files, images and scoped review evidence are included. Supplier correspondence, account/order information and unrelated workshop files are excluded. Local provenance paths in reports were converted to package-relative paths; the native PCB, schematic and footprint bytes are preserved.
