# F1 compact replacement — selection evidence

Selected 30 October 2026; supply description updated 31 October 2026. Component selection and metadata review only; no hardware qualification.

## Selected component

**Littelfuse 08853.15DR, NANO2 885, 3.15 A**, soldered surface-mount fuse. The [manufacturer datasheet](https://www.littelfuse.com/~/media/electronics/datasheets/fuses/littelfuse_fuse_885_datasheet.pdf.pdf) supplies the specifications and ordering-code construction; the [manufacturer declaration](https://www.littelfuse.com/assetdocs/reach211-declaration-08853?assetguid=c82a85cc-e19d-4b77-bfab-a49e8694a167) independently names this exact MPN.

- Body: 10.86 ±0.23 × 4.78 ±0.10 × 4.78 ±0.10 mm.
- Interrupting rating for this current variant: **1,500 A at 125 VDC**. The separate 100 A at 500 VDC rating must not be confused with it.
- Nominal cold resistance: 19.6 mΩ. Nominal melting I²t: 13.35 A²s, specified at 10× rated current; this is not a guaranteed total clearing-energy limit.
- Opening characteristics: 125% rated current, 1 hour minimum; 200%, 120 seconds maximum; 1,000%, 1 second maximum. It is not a precise 3.15 A trip threshold.
- Manufacturer continuous-current derating is 25%, with additional temperature derating. This gives 2.36 A at reference ambient before temperature correction.

## Land pattern and space

Use native KiCad `Fuse:Fuse_Littelfuse-NANO2-885`. Pad centres are x = −5.275/+5.275 mm; each pad is 5.625 × 7.255 mm. These dimensions implement the manufacturer's recommended lands: 5.6 +0.05/−0 by 7.23 +0.05/−0 mm with a 4.9 +0.05/−0 mm gap. Do not shrink the lands to the body width merely to gain logo space.

The installed native footprint courtyard is **16.74 × 7.76 mm**, approximately 130 mm². The former Schurter 0031.8201 holder footprint courtyard is **26.00 × 10.10 mm**, approximately 263 mm². This reduces the reserved footprint area by about 50%; actual usable silkscreen space still depends on copper, neighbouring components and placement. The holder, cartridge and black cover are removed together. Replacement now requires soldering.

## Circuit purpose and remaining checks

Keep F1 between `BAT_PROTECTED` and `HOST_BUCK_IN`, protecting only the input branch of the integrated MP9447 5 V supply for the Orange Pi. The existing external 15 A pack fuse remains. Estimated 15 W output demand corresponds to approximately 1.3–2 A input over the selected battery/efficiency assumptions; the upper estimate leaves limited warm-enclosure margin after derating.

Before hardware acceptance, check startup pulse energy and repetition, maximum continuous input current, enclosure temperature, available battery fault current, conductor withstand, and coordination with the external fuse and converter protections. Neither a high interrupting rating nor a clean PCB DRC proves that the fuse opens before every downstream conductor or semiconductor is damaged.

PCBWay sourcing and pricing are unconfirmed. No availability or production approval is implied.

## Metadata check

The current contract in `electrical/circuit.json` and the grouped assembly BOM both select exact MPN `08853.15DR`, manufacturer Littelfuse and the native 885 footprint. The contract assigns pin 1 to `BAT_PROTECTED` and pin 2 to `HOST_BUCK_IN`. The generated local footprint alias `MOSS:Fuse_Fuse_Littelfuse-NANO2-885` is consistent with the project library. No F1 metadata mismatch was found. Historical generators are not part of this package. No PCB was modified by the component-selection review.
