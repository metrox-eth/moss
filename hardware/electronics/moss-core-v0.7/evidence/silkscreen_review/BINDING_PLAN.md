# Independent silkscreen-only comparison

`check_silk_only.py` is prepared for the **frozen** candidate. It reads native KiCad S-expressions directly, without opening or saving the design and without invoking a router or solver. No final candidate review has been run at preparation time.

```sh
python3 check_silk_only.py --baseline BASELINE_DESIGN --candidate FROZEN_DESIGN --leader-manifest REFERENCE_LAYOUT.json --output SILK_ONLY_EQUIVALENCE.json
```

The protected comparison retains every footprint UUID, reference/value string, pose, pad, local model transform, net, copper segment, via, filled zone and outline. Reference/Value field presentation and text on Fab/Silk layers are removed. Text on copper, mask or paste layers is protected. Every pre-existing non-text graphic remains protected; the narrow exception for new leader UUIDs is described below. Electrical source/library/model files and the BOM/position CSVs are additionally compared byte for byte. If native serialization alone changes number spelling or collection order, the canonical comparison preserves equivalent values without changing polygon vertex order.

The sole source exception is the **top-level `notes` array** in `electrical/BOM_PCBWAY_ASSEMBLY.json`, to replace the old package name and document the ink update. The report records both file hashes, every old/new note, added/removed notes and the canonical non-notes hash. All MPNs, designator groups, quantities, counts and other data must remain exact. The supplier BOM CSV and positions CSV remain byte-identical. A permitted note change is never reported as byte identity.

New callout segments are allowed **only by exact UUID whitelist** from `REFERENCE_LAYOUT.json`. Each declared `graphic_uuids` entry must be absent from the baseline and present as a new `gr_line` or `fp_line` on the declared F/B Silk face, with matching endpoints and width of at least0.15mm. The report records every accepted native UUID, endpoints, face, stroke and object hash. Native-coordinate tolerance is2nm to allow conversion of half-nanometre placement coordinates to saved integer units. No existing graphic may be deleted or modified. `fp_line` declarations additionally require an explicit `footprint_local` coordinate frame and matching footprint owner, avoiding an unverified back-side transform. All other native objects remain protected.

The style check applies the published PCBWay thresholds to new/changed **visible Silk** text: at least0.8mm font height and0.15mm strokes. Existing small Fab text is not a printed legend and is not treated as a new failure. Opening clearance is a separate geometry/DRC/preview check; this script does not pretend a text bounding box proves0.15mm clearance from the actual strokes to mask openings.

## Link the previous evidence without inventing a new test

Keep the old reports with their original input hashes. Add one explicit applicability record containing:

1. Baseline PCB hash, final PCB hash, this comparator's hash and its passing result.
2. Exact hashes of the original ERC/DRC, power/ground and mechanical evidence files.
3. `inheritance = exact protected native geometry and byte-identical electrical contract`; `electrical_simulation_rerun = false`.
4. The separate fresh native silkscreen DRC, opening-clearance check and rendered-image inspection.

The previous power/ground and mechanical results then apply to unchanged geometry. The logic model still matches the same circuit/netlist hashes. Firmware GPIO assignments, source and binary remain unchanged; a metadata link can associate the same firmware evidence with the new presentation-only PCB hash. It must not imply that firmware was flashed or that physical hardware tests were performed.

Regenerate the actual Silk Gerbers/previews and update package/manifests/ZIPs together. The new Gerber hashes are export outputs, not evidence of changed copper. If an exporter rewrites creation timestamps, distinguish those header changes from actual copper/mask/paste/drill geometry. Retain subtraction of mask from Silk, but do not accept a new reference merely because an exporter can clip its strokes away.

## Remaining visual checks after previews exist

- The printed reference belongs unambiguously to its component, with consistent reading directions.
- No overlap, clipped character, port-label collision or text hidden under the Orange Pi/connector housings where it defeats identification.
- Both board sides are inspected at a useful scale; a clean flat render alone is not a clearance measurement.

Primary limits: [PCBWay text dimensions](https://www.pcbway.com/helpcenter/design_instruction/How_to_make_my_silkscreen_clear_and_beautiful_on_PCB__.html), [PCBWay spacing from openings](https://www.pcbway.com/helpcenter/Engineering_Questions/Spacing_between_silkscreen_and_openings.html).
