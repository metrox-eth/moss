# 3D printing

Choose one hull, one upper cover, one computer carrier and one camera option. Print each shared STL in the **quantity shown**, rather than downloading a separate copy for every wheel or axle position. The catalogue has **73 distinct STL files** across all options.

With a one-piece hull and cover: **106 pieces for Pi + RealSense, 107 for Pi + Gemini, 108 for Jetson + RealSense, or 109 for Jetson + Gemini**. Each split option adds one piece.

**Jetson builders:** print one JT01 and one JT02 in PETG. These different retaining tabs are included in the current archive and on the Jetson plate in both 3MF projects.

## Ready-to-print 3MF plates

Download **one** project and open it in Bambu Studio. The quantities, part orientations, materials and automatic tree supports are already set. Choose the matching printer and your filament before slicing.

| Project | Hull and cover | Common plates | Computer: choose one | Camera: choose one |
|---|---|---|---|---|
| [H2S — 21 plates](https://github.com/metrox-eth/moss/releases/download/v0.6-r92/MOSS_V06_R92_H2S_Print_Plates.3mf) | One piece each | 1–17 | 18 Jetson **or** 19 Pi | 20 Gemini **or** 21 RealSense |
| [P1 / P2 — 24 plates](https://github.com/metrox-eth/moss/releases/download/v0.6-r92/MOSS_V06_R92_256mm_Split_Print_Plates.3mf) | Split hull and split cover | 1–20 | 21 Jetson **or** 22 Pi | 23 Gemini **or** 24 RealSense |

The compact profile is published for P1S, P1P and P2S. Both projects include the two Jetson retaining tabs on the Jetson plate. The copies of shared spacers and wheels are already placed; do not multiply them again. Each plate uses one material.

Standard 0.20 mm settings, 0.4 mm nozzle, **15% gyroid for all parts** and **automatic tree supports**. Keep the supplied orientations. For the split hull and cover, follow the epoxy and fastening steps in the assembly guide.

[See every plate and its contents](https://www.showrobotics.ai/moss/build/print-plates.html).

| Material | Parts |
|---|---|
| PETG | Hull, motor supports, transmission, electronics carriers, camera inserts and LiDAR mounts |
| PLA | Cover, bin, arm plate, arm and gripper body |
| TPU95A | Tracks |

Use the standard/default profile and **15% gyroid infill**. Enable **automatic tree supports** with the default support settings.

The STL files are oriented for printing. The [visual catalogue](https://www.showrobotics.ai/moss/build/#print) shows the material and quantity for every part; the [CSV](docs/build/printed_parts.csv) gives the exact filenames.

## Choose the camera option

- RealSense: one RealSense support insert.
- Gemini: one flush insert and one window bezel. The thin straight bridges have been removed; the curved ends remain.

## Current set

The hull is R92, the motor supports R90, the Gemini window bezel R89, and both computer carriers R87. Each filename and catalogue entry carries its own part revision. The arm plate geometry remains R22.

The split hull has been rebuilt from the current R92 native geometry. Choose the single hull or the two halves in the catalogue. [Split-hull assembly and files](docs/build/SPLIT_HULL.md).

## Upper cover and outer track frames

Choose the [two-piece cover](docs/build/SPLIT_COVER.md) for a smaller build volume. Its two integral dovetails assemble from above and are glued before fitting the cover.

Print the outer track frames separately, flat, on the **front-right to rear-left diagonal**. Their STLs are already rotated. See the [bed placement diagram](docs/build/OUTER_FRAME_PRINTING.md).

All **38 spacers** are together on **H2S plate 5** or **P1 / P2 plate 8**. Print **four identical tensioner sliders** and rotate each to match its assembly position.
