# MOSS CORE V0.7 — Prototype

This is my first custom PCB for **MOSS, the litter-picking rover**, designed with Codex and KiCad. I am publishing the editable design so people with electronics experience can help review it before the first assembled prototypes are tested.

**Updated 31 October 2026.** The existing V0.7 Prototype files have been replaced with the design submitted for PCBWay review. This is still the first, unbuilt prototype; hardware revision letters are reserved for fabricated boards.

## What changed

- **One six-wire cable per motor:** J3/J4 now carry winding power and encoder signals together. J2 combines the Cytron controls and its four bridge outputs; J11 retains the separate supply. The propulsion interface uses four connections instead of six. See the [motor wiring guide](MOTOR_WIRING.md).

- The Orange Pi's **5 V converter is now integrated into the PCB**, using MP9447GL-Z, L3 and their supporting components. The separate Waveshare module is removed. J20 remains a **5 V / 3 A** USB-C power output.
- **H1 now provides a GND connection:** a plated 2.7 mm mounting hole with an exposed copper ring on both sides and eight stitching holes. It accepts a bonding lead; the hole alone does not earth the rover or establish ESD protection.
- Common solder-mask openings on **U14, U17 and U43** replace bridges too narrow for the manufacturer's process. This mask correction preserves the copper, drills and solder-paste apertures.
- **U2 is now TPD2E2U06QDCKRQ1**, with the same DCK/SC70 footprint and pin assignment. Assembly notes include its MSL2 handling requirements, support for J7 insertion and manual placement of J8.

KiCad sources, BOM, placement data, Gerbers, drills and the views below all correspond to this update.

![MOSS CORE V0.7 Prototype, component side](preview/BOARD_TOP.png)

![MOSS CORE V0.7 Prototype, underside](preview/BOARD_BOTTOM.png)

## What the board does

The four-layer board has an 80 × 75 mm main body and two local connector-support ears, for an **82 × 75 mm overall outline**. Mounting holes are unchanged. It combines an ESP32-S3 controller, a powered half-duplex serial-servo interface, Cytron control and encoder interfaces, left/right motor-current sensing, battery-voltage measurement, an I2S speaker amplifier and an integrated Orange Pi power supply. The Cytron motor driver and USB hub remain external.

The arm uses one daisy-chain connector for the standard six-servo configuration, or seven with the optional twin shoulder. The selected connector and the actual common power harness still need aggregate-current qualification. Core firmware needs its own port and commissioning; this is not a drop-in replacement for the existing controller firmware.

The current design includes two chassis-fan outputs, corrected connector legends, the six-position stop connector with two deliberately unwired positions, and a compact soldered **Littelfuse 08853.15DR, 3.15 A**, on the Orange Pi supply input branch. F1 has no separate holder, cartridge or cover; replacement requires soldering. F2/F3 are separate 1 A audio/fan branch fuses, and the external 15 A pack fuse remains required.

The fan outputs carry fused 3S battery voltage, up to 12.6 V, rather than regulated 12 V. Their combined 0.2 A running current is an estimate, not a measurement. See the [connector guide](CONNECTORS.md) and [F1 selection evidence](evidence/F1_SELECTION.md).

## Harness packaging study

The separate [harness study](harness/) contains a 3D viewer, film and hull prototype with cable-tie supports. **Its geometry is frozen to the 30 October board with the separate Waveshare module.** It has not yet been updated or physically fitted to this integrated-power design.

## Download and inspect

- [Complete prototype review package](delivery/MOSS_CORE_V07_PROTOTYPE_REVIEW_20261031_HARNESS.zip).
- [KiCad project](electrical/MOSS_Core_V07_Prototype.kicad_pro), [PCB](electrical/MOSS_Core_V07_Prototype.kicad_pcb) and [root schematic](electrical/MOSS_Core_V07_Prototype.kicad_sch).
- [Physical-pin circuit contract](electrical/circuit.json), local symbols and footprints in `electrical/`.
- [Grouped component BOM](delivery/assembly/MOSS_CORE_V07_PROTOTYPE_BOM.csv) and [placement file](delivery/assembly/MOSS_CORE_V07_PROTOTYPE_POSITIONS.csv): **208 placed components, 96 purchase articles**. The native board also contains mounting holes and test pads, for 222 footprints total.
- [Gerbers and drills](delivery/MOSS_CORE_V07_PROTOTYPE_GERBERS_20261031_HARNESS.zip), with [fabrication notes](delivery/fabrication/FABRICATION_NOTES.txt) and [assembly notes](delivery/assembly/ASSEMBLY_NOTES.txt).
- [File hashes](MANIFEST.json), [check results](evidence/CHECKS.json) and [publication provenance](evidence/PUBLICATION_NOTES.json).

Use KiCad 10. Open the project from `electrical/` so `${KIPRJMOD}` resolves its local libraries and models. Preserve the native-board model settings when updating footprints: some library defaults reference KiCad's installed models. Several custom models are visual approximations, not manufacturer mating CAD. The previews add a simple U60 package body, documented in [visual provenance](preview/VISUAL_PROVENANCE.json); the native PCB is unchanged.

The published PCB bytes match the adopted prototype:

```text
SHA-256: ea19d9bdb0b6037542eb0b4bca53a04d0b0fecbf3d16e4198485bf43dcadbfc4
```

## Community review welcome

**Not fabricated or hardware-qualified yet.** The recorded [ERC](evidence/ERC.json) has zero violations. The [PCB DRC](evidence/DRC.json), under the saved project rules, has zero errors, zero missing connections and zero schematic-parity issues. Two pre-existing dangling-track warnings remain on `PWM_L` and `BAT_PROTECTED`. These are static checks, not powered test results.

I would especially welcome review of:

- Exact component/pin/footprint matching and connector mating/polarity.
- Power distribution, conductor sizing, return paths, decoupling and routing.
- Integrated-converter startup, ripple and stability with the existing output capacitance, load transients, fuse coordination and thermal behavior.
- The shared servo connector/harness current, actuator-cutoff behavior and motor regeneration/BMS interactions.

The new motor paths use the supplier data for the 90:1 / 110 rpm motors (up to 1 A rated and 2.3 A stall at 12 V), rather than the Cytron's 10 A channel headline. This quotation requests 1 oz copper on all four layers. Load/thermal tests and fault-protection coordination remain necessary; a clean DRC does not establish those ratings.

These remain open design and bench-validation topics. The fan connector identity/current and stop-button contact arrangement also need physical confirmation. No firmware or real-load test result is implied by the views or static checks.

Please [open an issue](https://github.com/metrox-eth/moss/issues) with **MOSS CORE V0.7 Prototype**, the component/net reference, and the relevant datasheet or calculation. Corrections and practical suggestions are very welcome.

## Editing and re-export

Edit the native KiCad design in this folder. Update the circuit contract and assembly BOM when components change. `python3 tools/export_package.py` runs the native checks and regenerates the delivery files. It stops on errors, missing connections, parity differences or an unexpected assembly inventory. `--reuse-checks` requires every recorded design-file hash to match the successful checks. Review the results before manufacturing or powered tests.

## License and provenance

MOSS hardware design: [CERN-OHL-S-2.0](LICENSE-HARDWARE). Documentation/media: CC BY 4.0, as described in the repository [NOTICE](NOTICE). Bundled KiCad library material retains its [upstream license and exception](KiCad_Libraries_LICENSE.md).

Supplier correspondence, account/order information and unrelated workshop files are excluded. Local provenance paths in reports were converted to package-relative paths. The native PCB, schematic, footprints and matching fabrication/assembly data are preserved.
