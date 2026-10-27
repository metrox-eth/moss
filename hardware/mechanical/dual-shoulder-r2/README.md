# MOSS — SO-101 dual-servo shoulder, R2

Two shoulder servos sit back to back in one printed housing. A wider upper-arm fork connects their two outward-facing horns in direct drive. The original base pivot, shoulder height and elbow interface are retained.

**[Open the assembled CAD](CAD/MOSS_Dual_Shoulder_R2_Z_Up.step) · [Printable STLs](STL/) · [Individual STEP files](CAD/)**

![The R2 dual shoulder fitted to MOSS, rendered from CAD](images/moss-dual-shoulder-r2.png)

## Print these two parts

| Qty | Part | Print file | Editable CAD |
|---:|---|---|---|
| 1 | Common shoulder housing | [Shoulder monobloc STL](STL/01_Shoulder_Monobloc_R2.stl) | [STEP](CAD/01_Shoulder_Monobloc_R2.step) |
| 1 | Wider upper-arm fork | [Dual upper arm STL](STL/02_Upper_Arm_Dual_R2.stl) | [STEP](CAD/02_Upper_Arm_Dual_R2.step) |

**PLA · 15% gyroid infill · automatic tree supports with the default support settings.** Keep the supplied STL orientation. These are replacement parts for the existing shoulder housing and upper arm.

## Parts and screws

| Qty | Item | Where it goes |
|---:|---|---|
| 2 total | Matching ST3215 12 V shoulder servos | One existing shoulder servo plus one matching servo; same voltage and gear reduction |
| 4 | M2 × 6 servo-kit screws | Hold the two servo cases in the housing: two screws on each outside face |
| 8 | M3 × 6 screws | Fix the fork to the two output horns: four per horn |
| 2 | Horn centre screws supplied with the servos | One in each output horn |
| 1 | Additional compatible servo bus cable | Connect the second shoulder servo |

Reuse the base-pivot and elbow fixings from the original arm. The CAD was dimensioned around the ST3215 reference bodies; check the fit before substituting another servo model.

## Assemble

1. Switch off the arm power and support the arm. Remove the original shoulder housing and upper arm, keeping the base-pivot and elbow hardware.
2. Feed the two servo cables through the bottom openings. Lower both servos into the common housing from above, back to back, with their driven shafts facing outward.
3. Install **four M2 × 6 screws**, two from each outside face. The printed walls locate and support the servo cases.
4. Fit the wider fork to the outward-facing horns at the intended neutral pose, without forcing the two servos against each other. Secure it with **eight M3 × 6 screws**, four per horn, and the **two supplied horn centre screws**. Refit the elbow and the rest of the arm.
5. Complete the paired-servo controller's zeroing procedure before the first powered movement. Check synchronized movement without a payload before trying a pickup.

![Exploded view of the common housing, two reference servos and upper arm](images/exploded.png)

## Paired-servo control

The two output shafts face opposite directions. Their relative movements must be mirrored, with a calibrated zero for each servo, so the pair does not fight through the fork.

The [arm software documentation](../../../docs/arm.md) describes the existing MOSS arm stack. Its six-servo configuration is the original single-shoulder arrangement; the second shoulder servo requires paired-servo control. This folder supplies the mechanical design, not a replacement firmware image.

For the load and synchronization study, see the separate [dual-shoulder simulation proposal](https://github.com/metrox-eth/moss/pull/9).

## Size and status

- Common housing: **about 86 mm wide**.
- Two reference servos, including protrusions: **80.4 mm across**, with about **1.2 mm** between the closest rear protrusions.
- Upper-arm fork: **108.3 mm maximum width**, including its cable clip.
- Shoulder height: **unchanged** from the original MOSS mounting.

The published geometry is the R2 prepared on 26 October 2026. On 27 October, Laurent reported that the dual-servo setup had been tested with Iris. Detailed load, temperature and endurance measurements are not included in this package.

The [CAD check report](validation/CAD_CHECKS_2026-10-26.json) predates that workshop report. It records valid solids and watertight print meshes, servo insertion, outside screw access and sampled arm clearances. Its `physical_tests_performed: false` describes those original numerical checks. It is not a payload rating or an exhaustive check of every arm trajectory.

## Files and credits

All dimensions are in **millimetres**. The assembled STEP uses **Z up** and contains the two printed parts. Individual STEP files retain the design coordinate frame; STLs are oriented on the print bed. Servo models in the pictures are visual references.

Derived from the [SO-101 by The Robot Studio](https://github.com/TheRobotStudio/SO-ARM100). The original shoulder and upper-arm STEP inputs, pinned source revision and checksums are in [source/](source/). Changes for MOSS: a common two-servo housing, exterior screw access, cable openings and a tapered wider fork.

See [NOTICE](NOTICE), the retained [SO-101 Apache-2.0 licence](LICENSE-SO101), and the repository's [hardware licence](../../../LICENSE-HARDWARE). Delivered CAD/STL and source-file hashes are recorded in [manifest.json](manifest.json).
