# MOSS CORE V0.7 — mounting dimensions

Updated 1 November 2026. The PCB outline is **82 × 79 mm**, with 2 mm corner radii. The four Core fixing centres are **4 mm from the nearest outer edges**, for a **74 × 71 mm** centre-to-centre pattern. The hull mounting posts will be adapted to this pattern; the earlier hull fixing positions must not be reused unchanged.

Dimensions below use the **top-left of the board outline as (0, 0)**, X to the right and Y downward, viewed from the component side.

| Hole | X (mm) | Y (mm) | Finished hole |
|---|---:|---:|---|
| H1 — GND | 4 | 4 | Ø2.7 mm plated |
| H2 | 78 | 4 | Ø2.7 mm non-plated |
| H3 | 4 | 75 | Ø2.7 mm non-plated |
| H4 | 78 | 75 | Ø2.7 mm non-plated |

These are M2.5 fixing holes. H1 has a Ø5.4 mm exposed GND ring on both faces and eight Ø0.5 mm plated stitching holes. The printed rings around H2–H4 have the same outer diameter; they are silkscreen, not exposed copper. A declared Ø6 mm screw-head/washer envelope leaves 1 mm to the straight board edges.

The KiCad drawing uses outline bounds X = −2…80 mm and Y = −4…75 mm. Its native hole coordinates are H1 (2,0), H2 (76,0), H3 (2,71), H4 (76,71).

**H5–H8, the four Orange Pi standoff holes, stay in their existing positions.** The upper assembly clearance study uses 20 mm standoffs and a measured 16 mm total SBC/cooler height. Route the J2 and J3 cable bundles outward as described in [the connector guide](CONNECTORS.md).

The H5–H8 indicators are white printed rings on both faces: Ø4.2 mm outside, Ø3.0 mm inside, with a 0.6 mm band. They leave 0.15 mm around the Ø2.7 mm holes.
