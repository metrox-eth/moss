# MOSS R92 — mechanical changes

## 9 November 2026 — Important Safety Update

- Replaced the small main switch with a round KCD1-5-101EN, listed for 20 A at 12 V DC.
- Specified a DC099 rear charging socket and 18 AWG leads for the complete 5 A charging connection. Rover power stays on XT30 with the existing 15 A pack fuse.
- Updated the one-piece and split hulls, Fusion/STEP sources, both 3MF projects, BOM and assembly instructions. The rear socket uses an 11 mm mounting hole; the switch uses a keyed 20 mm opening.


## 24 October package update

- Replaced the two-port USB hub with the Hoco HB1 four-port USB 2.0 hub.
- Added one GameSir Nova 2 Lite gamepad with its wireless USB receiver for manual driving.
- Grouped all 38 spacers on one plate: H2S plate 5 or P1 / P2 plate 8. The profiles still contain 21 and 24 plates, respectively.
- Consolidated the rotation-equivalent tensioner sliders into one `Tensioner_Slider` reference, quantity 4. Rotate the same part for its assembly position.
- The archive now contains 73 distinct printable STL files, both Jetson retaining tabs and both 3MF projects. The number of physical parts per rover is unchanged.
- Original part meshes and print orientations are retained. The revised layouts were checked in Bambu Studio; this packaging update does not claim new physical print tests.


This is the matched current print set prepared on 16 October 2026.

## Changes carried into this set

| Part | Current revision | Change |
|---|---|---|
| Hull | R92 | Repaired the small Cytron-to-wall junction. |
| Hull partition | R81 | Enlarged the cable opening while preserving the screw supports. |
| Reinforcement ramps | R82 | Restored the missing outer ramps. |
| Fan clips | R83 | Moved each opposing clip 0.5 mm inward. |
| Heat-set insert pockets | R84 | Eleven locations now use M3 inserts with 4 mm outer diameter and 6 mm length. |
| Audio mounts | R85 | Speaker screw spacing increased 1 mm; amplifier moved 2 mm and gained two support pillars. |
| Rear electronics | R86 | Fans, clips and vents lowered 2 mm; Cytron and ESP supports lowered 4 mm. The approved rounded relief under the Cytron keeps the motor clearance. |
| Computer mounts and carriers | R87 | Rear posts reduced to 9 mm diameter and shifted 5 mm toward the computer; Jetson and Pi carriers updated together. Motor-hatch groove cleared. |
| Gemini window bezel | R89 | Removed only the two thin straight bridges; retained the curved ends and pointed tips. |
| Motor supports | R90 | Added 8 mm upper corner radii. |
| Assembly orientation | R91 | Restored Z-up orientation with the hull base atZ0. |
| Upper cover | R10 split option | Cut at the arm-platform corner, with two integral dovetails assembled from above and glued. |
| Outer track frames | R32 | Geometry unchanged; STL print orientation rotated to the front-right / rear-left diagonal. |
| Arm plate | R22 | Geometry unchanged; exported again for this package. |
| Bin and gripper pads | Removed | The four TPU pads are no longer supplied as printable parts. |
| Tracks | R78 | Current 70-tooth print masters with the deeper guides. |

## What is included

- 74 distinct part STL files covering hull, computer and camera alternatives, plus two optional split-joint coupons.
- 106–111 printed pieces depending on the computer, camera, hull and cover options.
-Editable Fusion source with 99 solid parts,8 arm mesh parts and 2 track mesh masters.
-STEP with 99 solid parts:96 manifold solids and 3 solids with internal voids.
- 113 current part previews, an overview image, a per-part material list and standard print settings.
- 20 assembly cards and seven clips in one visual style: a reference guide, five exploded assemblies and the corrected road-wheel fastening example.
- All 38 printed track spacers have guide references SP01–SP12. The 18 purchased shaft collars use LK05/LK06/LK08, with dimensions in the BOM and part-reference list.

## What is kept separate

The split-hull alternative is rebuilt from the current R92 geometry, with six M4 fixings and the joint clearances.

This mechanical package uses the existing separate electronics modules.

## Validation scope

All 113 part STL meshes are closed, have consistent winding and positive volume. Their geometry was reconciled with the current CAD; the 99 retained solid-part comparisons and the new split-hull and split-cover comparisons differ by less than 0.3%. Tiny export-seam repairs are recorded in `release/data/tessellation_repairs.json` and `release/data/SPLIT_HULL_R92_CHECKS.json` and do not move the intended CAD contours.

The native archives passed every internal archive CRC check. The STEP contains all 99 named solid parts. These checks establish file and geometry consistency; they do not substitute for physical assembly or the planned field test.


- Current R92 hull split into two printable halves; native Fusion sources and optional local fit coupons included.

The [two-piece upper cover](SPLIT_COVER.md) uses top-entry dovetails. The [outer track frame guide](OUTER_FRAME_PRINTING.md) shows the front-right to rear-left placement.

## 18 October print package

- 74 distinct part STLs with total quantities, plus two optional hull-joint fit coupons.
- Both Jetson retaining tabs, JT01 and JT02, with their STEP sources.
- H2S: 21 prepared plates, one-piece hull and cover.
- P1 / P2: 24 prepared plates, split hull and cover. The two pieces on cover plate 13 have been spaced apart to clear their supports.
- Standard 0.20 mm settings, 15% gyroid and automatic tree supports; all parts, including TPU tracks, use 15% gyroid.
- Choose one computer plate and one camera plate. No part geometry was changed or remeshed for this packaging update.

See [the plate guide](PRINT_PLATES.md) for the exact plate numbers. The original 16 October archive remains available; use the new 18 October archive for the complete current package.
