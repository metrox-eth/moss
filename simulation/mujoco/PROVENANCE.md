# Geometry provenance and validation boundary

## R92 release geometry

The solid components were tessellated from the published
[`MOSS_Printable_BRep_Parts_R92.step`](https://github.com/metrox-eth/moss/releases/download/v0.6-r92/MOSS_Printable_BRep_Parts_R92.step).
Its SHA256 is
`85e663ca8b7b784560de1649d18552fe11d97ee142986222d70d54dcbe573aeb`.
The source was checked against GitHub's release-asset digest on 26 October 2026.

STEP assembly placements were retained. OpenCascade/CadQuery tessellation used
0.15 mm linear and 0.15 rad angular deflection settings. These are mesh generation
settings, not measured manufacturing or simulation accuracy. The configuration
selects common parts, the Jetson carrier and the RealSense insert. Alternative
Pi/Gemini and split-print assemblies are not superimposed on the model.

The eight printed SO101 shells use their original indexed geometry, matched
against the R92 STL volume and assembly bounds. The correspondence to the print
orientation is recorded in `reference/print_to_rig.json`: scale the published STL
from millimetres to metres, then apply that rigid transform. One degenerate
triangle in the base motor holder is omitted. Registration errors are numerical
mesh correspondence checks, not hardware calibration results.

Six existing SO101 housing meshes retain their upstream Apache-2.0 provenance.
The mounted belts come from the saved R92 assembly reference. Both retain all
513,216 original triangles, in OBJ format to avoid MuJoCo's binary-STL face-count
limit; no voxel remeshing or decimation is used. Their centre separation is
270 mm, and their minimum Z establishes the ground origin.

Individual assets, input filenames/hashes, licences, rig assignments, triangle
counts and world-space bounds are recorded in `model/manifest.json`. Runtime
requires only the files included here, not the original Fusion installation,
CAD export folders, or older simulation package.

## Arm and gripper

Joint definitions originate from [MuJoCo Menagerie SO101](https://github.com/google-deepmind/mujoco_menagerie/tree/0059d4335f8156206f63a35662313385f7ad6d74/robotstudio_so101),
commit `0059d4335f8156206f63a35662313385f7ad6d74`. The MOSS R31 collision-review
snapshot supplied its arm/tool rigid groups, NC90 slide/pinion relation and
decomposed colliders. The generator input in `reference/arm_skeleton.xml` retains
the joints/defaults and explicit contact exclusions, without the old chassis
geometry. R92 placement is applied in `reference/kinematics.json`.

Old moving-part colliders are reused only where the R92 geometry matches their
rig-local volume within 1% and world bounds within 0.5 mm; individual values are
recorded. This establishes correspondence for the reused approximation, not an
error bound for its contact surfaces. Other components use current per-part
convex hulls. The R92 bin is decomposed separately so its interior stays open.

The upstream arm gains/inertias and the estimated chassis/tool parameters have
not been fitted to MOSS measurements. The gripper's preliminary damping/friction
and position control replace values that had only been used for static pose
inspection. The current package is not Dirac Robotics' calibrated model.

## Reproduction scope

`tools/build_model.py` deterministically rebuilds both MJCF files from the shipped
assets and reference data. No external service or API is used. Re-tessellating
the manufacturing STEP requires an OpenCascade environment and preserving the
source assembly transforms, configuration selection and rig frames above.
Regenerating collisions can change results and requires re-running the tests.

Validation checks both stored asset hashes and the **compiled MuJoCo mesh
transforms** against the source assembly bounds. The checks also exercise
stationary integration, forward motion, turning, heading-relative motion,
small arm movements, coupled jaw motion, the bin cavity and a released object
settling inside it. These are offline software checks, not an autonomous pickup
trial or a measurement of real-world accuracy.
