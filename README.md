# MOSS Core V0.7 — electrical review

Lightweight snapshot of the current MOSS Core PCB, prepared on **5 November 2026**. It contains one design. The native KiCad files are unchanged from [the main MOSS repository at `89db394`](https://github.com/metrox-eth/moss/tree/89db394b67da0afb0144c24023628f015c6967d0/hardware/electronics/moss-core-v0.7).

**Open [`electrical/MOSS_Core_V07_Prototype.kicad_pro`](electrical/MOSS_Core_V07_Prototype.kicad_pro).** The matching top-level schematic and PCB are beside it. All schematic sheets, local symbols, footprints and custom rules are included.

This is the existing layout submitted for prototype review, not the separate Zap routing experiment. No boards have been hardware-qualified yet.

## Review brief

MOSS is a litter-picking rover. Core connects the ESP32-S3, six daisy-chained arm servos, an external Cytron MDD10A driving two track motors, encoders, audio, fans, a stop button and the Orange Pi supply. The optional dual shoulder adds a seventh servo.

For the first pass, report findings with component references and supporting evidence, without editing the design. Priorities:

- Battery and actuator current paths, connector limits, protection and motor regeneration. Motor winding leads are H-bridge outputs, not ground returns.
- The integrated Orange Pi 5 V supply and the logic supply: switching loops, decoupling, ground returns and possible resets under motor/servo load.
- Individual motor-current sensing, including the shunts and their sense connections.
- Stop, watchdog, supply-fault and rearm behavior; power recovery must not automatically resume old commands.
- Agreement between schematic, PCB, component part numbers and connector pinouts.

The reduced package was checked again with KiCad 10.0.6: zero ERC violations, zero DRC errors, zero missing connections and zero schematic/PCB parity issues. The two existing DRC warnings remain: one dangling copper end and one small silkscreen overlap. These are static checks, not hardware validation.

## Useful files

- [BOM.csv](BOM.csv): current assembly purchasing list.
- [Power and rearming](docs/POWER_AND_REARM.md).
- [Connector pinouts](docs/CONNECTORS.md) and [motor wiring](docs/MOTOR_WIRING.md).
- [Fabrication notes](docs/FABRICATION_NOTES.txt): layer and copper specifications.
- [MCU pin map](electrical/MCU_PIN_MAP.json).
- [Commissioning firmware](https://github.com/metrox-eth/moss/tree/89db394b67da0afb0144c24023628f015c6967d0/firmware/core-v0.7), in the main repository.
- `checks/`: fresh KiCad checks of this reduced package. `evidence/`: earlier design analyses for reference, not powered-board measurements.

PDFs, videos, 3D models, fabrication archives and earlier board variants are omitted. Datasheet links remain in the design and documentation. This package is intended for electrical review; full mechanical and manufacturing files remain in the source repository.

[SOURCE.json](SOURCE.json) records the source commit and individual file hashes. Hardware is under [CC BY-NC-SA 4.0](LICENSE-HARDWARE); third-party symbols and footprints retain their [KiCad library licence and exception](KiCad_Libraries_LICENSE.md). See [NOTICE](NOTICE) for the remaining licence scopes.
