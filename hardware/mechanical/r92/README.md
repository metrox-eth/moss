# MOSS R92 mechanical package

**[Download CAD, STL and both 3MF projects](https://github.com/metrox-eth/moss/releases/download/v0.6-r92/MOSS_R92_Mechanical_20261024.zip)** · [Build guide](https://www.showrobotics.ai/moss/build/) · [BOM](../../../BOM.md)

The 24 October package contains **73 distinct part STLs**, two optional hull-joint fit coupons, editable Fusion sources, STEP geometry, part previews and assembly clips. Both Jetson retaining tabs (**JT01 and JT02**) and their STEP sources are included.

Identical spacers and road-wheel halves share one STL, with the total quantity in the [print list](../../../docs/build/printed_parts.csv). Left/right parts with different geometry remain separate. The archive includes [legacy filename aliases](../../../docs/build/print_aliases.json).

## Ready-to-print 3MF plates

Download **one** project and open it in Bambu Studio. The quantities, part orientations, materials and automatic tree supports are already set. Choose the matching printer and your filament before slicing.

| Project | Hull and cover | Common plates | Computer: choose one | Camera: choose one |
|---|---|---|---|---|
| [H2S — 21 plates](https://github.com/metrox-eth/moss/releases/download/v0.6-r92/MOSS_V06_R92_H2S_Print_Plates.3mf) | One piece each | 1–17 | 18 Jetson **or** 19 Pi | 20 Gemini **or** 21 RealSense |
| [P1 / P2 — 24 plates](https://github.com/metrox-eth/moss/releases/download/v0.6-r92/MOSS_V06_R92_256mm_Split_Print_Plates.3mf) | Split hull and split cover | 1–20 | 21 Jetson **or** 22 Pi | 23 Gemini **or** 24 RealSense |

The compact profile is published for P1S, P1P and P2S. Both projects include the two Jetson retaining tabs on the Jetson plate. The copies of shared spacers and wheels are already placed; do not multiply them again. Each plate uses one material.

Standard 0.20 mm settings, 0.4 mm nozzle, **15% gyroid for all parts** and **automatic tree supports**. Keep the supplied orientations. For the split hull and cover, follow the epoxy and fastening steps in the assembly guide.

[See every plate and its contents](https://www.showrobotics.ai/moss/build/print-plates.html).


The original 16 October archive remains available for reference. Use the 24 October package for the current grouped files and prepared plates. CAD geometry is unchanged by this packaging update.

MOSS-owned hardware designs in this repository: [CC BY-NC-SA 4.0](../../../LICENSE-HARDWARE). SO-101 and NormaCore material retains its upstream Apache-2.0 licence and notices. Documentation and media: CC BY 4.0.

The existing R92 release downloads are unchanged and retain the licence terms included in those published packages.

All **38 spacers** are together on **H2S plate 5** or **P1 / P2 plate 8**. Print **four identical tensioner sliders** and rotate each to match its assembly position.
