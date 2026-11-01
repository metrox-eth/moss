# MOSS CORE V0.7 — Prototype

This is my first custom PCB for **MOSS, the litter-picking rover**, designed with Codex and KiCad. I am publishing the editable design so people with electronics experience can help review it before the first assembled prototypes are tested.

**Updated 1 November 2026.** The matched files below describe the current 1 November layout for PCBWay engineering review. This is still the first, unbuilt prototype; hardware revision letters are reserved for fabricated boards.

## What changed

- **Black board, white assembly markings:** large underside connector labels, thick mounting-screw rings and fine Orange Pi standoff circles on both faces. The byline aligns with the MOSS logo.
- **Connector access:** the top edge is extended to give the ten-contact connector a proper board margin; battery, servo and speaker connections use vertical headers, checked with their mating plugs and wire exits.

- **Clean rectangular outline:** 82 × 79 mm with rounded corners, no protruding connector-support ears. The mounting holes stay in place.
- **Strict routing angles:** all native track segments use horizontal, vertical or 45-degree directions, including internal layers. The general interconnect was routed afresh; the critical load and sensing routes were rebuilt where needed.
- **Cable placement:** both fan headers are shifted left along the lower edge; the speaker header remains on the right. Matching bottom-side legends and assembly positions are updated. Repeated functional IC and connector families were checked; the two branch fuses now share their orientation.

- **One six-wire cable per motor:** J3/J4 now carry winding power and encoder signals together. J2 combines the Cytron controls and its four bridge outputs; J11 retains the separate supply. The propulsion interface uses four connections instead of six. See the [motor wiring guide](MOTOR_WIRING.md).

- The Orange Pi's **5 V converter is now integrated into the PCB**, using MP9447GL-Z, L3 and their supporting components. The separate Waveshare module is removed. J20 remains a **5 V / 3 A** USB-C power output.
- **H1 now provides a GND connection:** a plated 2.7 mm mounting hole with an exposed copper ring on both sides and eight stitching holes. It accepts a bonding lead; the hole alone does not earth the rover or establish ESD protection.
- Common solder-mask openings on **U14, U17 and U43** replace bridges too narrow for the manufacturer's process. This mask correction preserves the copper, drills and solder-paste apertures.
- **U2 is now TPD2E2U06QDCKRQ1**, with the same DCK/SC70 footprint and pin assignment. Assembly notes include its MSL2 handling requirements, support for J7 insertion and manual placement of J8.

KiCad sources, BOM, placement data, Gerbers, drills and the views below all correspond to this update.

![MOSS CORE V0.7 Prototype, component side](preview/BOARD_TOP.png)

![MOSS CORE V0.7 Prototype, underside](preview/BOARD_BOTTOM.png)

## What the board does

The four-layer board has an **82 × 79 mm rounded rectangular outline**, without protruding ears. Mounting holes are unchanged. It combines an ESP32-S3 controller, a powered half-duplex serial-servo interface, Cytron control and encoder interfaces, left/right motor-current sensing, battery-voltage measurement, an I2S speaker amplifier and an integrated Orange Pi power supply. The Cytron motor driver and USB hub remain external.

The arm uses one daisy-chain connector for the standard six-servo configuration, or seven with the optional twin shoulder. The selected connector and the actual common power harness still need aggregate-current qualification. Core firmware needs its own port and commissioning; this is not a drop-in replacement for the existing controller firmware.

The current design includes two chassis-fan outputs, corrected connector legends, the six-position stop connector with two deliberately unwired positions, and a compact soldered **Littelfuse 08853.15DR, 3.15 A**, on the Orange Pi supply input branch. F1 has no separate holder, cartridge or cover; replacement requires soldering. F2/F3 are separate 1 A audio/fan branch fuses, and the external 15 A pack fuse remains required.

The fan outputs carry fused 3S battery voltage, up to 12.6 V, rather than regulated 12 V. Their combined 0.2 A running current is an estimate, not a measurement. See the [connector guide](CONNECTORS.md) and [F1 selection evidence](evidence/F1_SELECTION.md).

## Orange Pi assembly clearance

The combined [mechanical review](evidence/MECHANICAL_REVIEW.json) uses **20 mm Orange Pi standoffs**, a CAD mounting height, and the measured **16 mm total Orange Pi/cooler height**. The 82 × 79 mm Core board clears the hull in this assembly. The component bodies clear the Orange Pi and four standoffs, including a 6 mm diameter standoff reservation. The conservative vertical gap from the highest component beneath the Orange Pi to its lowest underside feature is **4.15 mm**.

The mated-connector and wire checks use supplier dimensions where available and declared clearance envelopes elsewhere. **Route J2's wires rearward and J3's wires leftward, away from the Orange Pi, before bringing them upward.** A straight, expanded vertical bundle reservation at these two ports intersects the Orange Pi CAD. This is an assembly routing condition; the exact cable and connector tolerances still need checking on the first prototype. The cooler's lateral shape was not supplied, so its final cable clearance also needs checking.

The [outward cable-route check](preview/CABLE_CLEARANCE_ROUTES.png) uses declared 5 mm bundles with 10 mm bend radii. These example routes clear the supplied Pi, standoffs and hull CAD, plus the conservative cooler envelope; they are clearance reservations, not manufacturing drawings for a finished harness. [Intersection results](evidence/CABLE_CLEARANCE_ROUTES.json).

The [assembly view](preview/ASSEMBLY_CLEARANCE.png) shows the positions and reservations. The [power/ground check](evidence/POWER_AND_GROUND.json), [696-pin consistency check](evidence/DESIGN_CONTRACT.json) and [routing-angle check](evidence/TRACK_ANGLES.json) are tied to the same native-board hash. These are static design checks, not powered or thermal test results.

## Harness packaging study

The separate [harness study](harness/) contains a 3D viewer, film and hull prototype with cable-tie supports. **Its geometry is frozen to the 30 October board with the separate Waveshare module.** It has not yet been updated or physically fitted to this integrated-power design.

## Download and inspect

- [Complete prototype review package](delivery/MOSS_CORE_V07_PROTOTYPE_REVIEW_20261101_LAYOUT.zip).
- [KiCad project](electrical/MOSS_Core_V07_Prototype.kicad_pro), [PCB](electrical/MOSS_Core_V07_Prototype.kicad_pcb) and [root schematic](electrical/MOSS_Core_V07_Prototype.kicad_sch).
- [Physical-pin circuit contract](electrical/circuit.json), local symbols and footprints in `electrical/`.
- [Grouped component BOM](delivery/assembly/MOSS_CORE_V07_PROTOTYPE_BOM.csv) and [placement file](delivery/assembly/MOSS_CORE_V07_PROTOTYPE_POSITIONS.csv): **208 placed components, 96 purchase articles**. The native board also contains mounting holes and test pads, for 222 footprints total.
- [Gerbers and drills](delivery/MOSS_CORE_V07_PROTOTYPE_GERBERS_20261101_LAYOUT.zip), with [fabrication notes](delivery/fabrication/FABRICATION_NOTES.txt) and [assembly notes](delivery/assembly/ASSEMBLY_NOTES.txt).
- [File hashes](MANIFEST.json), [check results](evidence/CHECKS.json) and [publication provenance](evidence/PUBLICATION_NOTES.json).

Use KiCad 10. Open the project from `electrical/` so `${KIPRJMOD}` resolves its local libraries and models. Preserve the native-board model settings when updating footprints: some library defaults reference KiCad's installed models. Several custom models are visual approximations, not manufacturer mating CAD. The previews add a simple U60 body and manufacturer-based ESP32/IC markings, documented in [visual provenance](preview/VISUAL_PROVENANCE.json); the native PCB is unchanged.

The native candidate PCB is identified by:

```text
SHA-256: 9f0ef9f1bc34934417560cd6f2751c714f3643d7959bae822c8b48c13b259b03
```

## Community review welcome

**Not fabricated or hardware-qualified yet.** The recorded [ERC](evidence/ERC.json) has zero violations. The [PCB DRC](evidence/DRC.json), under the saved project rules, has zero errors, zero missing connections and zero schematic-parity issues. Two bounded warnings are documented in the check report: a retained free copper tip on the battery branch, and a tiny C21 silkscreen clip. The latter is removed from the production ink by the explicit solder-mask subtraction during Gerber export; it does not change copper or drills. These are static checks, not powered test results.

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
