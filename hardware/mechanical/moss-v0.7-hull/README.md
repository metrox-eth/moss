# MOSS V0.7 hull — 74 × 71 mm Core mounting

This hull matches the **82 × 79 mm MOSS Core PCB**. Three floor bosses move to the new mounting pattern; the fourth stays in place. The five integral cable-tie bridges and the rounded battery-divider wire notch are retained.

| File | Contents |
|---|---|
| [Print STL](stl/Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.stl) | Current hull, five tie bridges and wire notch |
| [Editable solid STEP](cad/Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.step) | Same complete hull geometry |
| [Base F3D](cad/Hull_MOSS_V07_Core_74x71_EDITABLE.f3d) | Current mounting hull before tie bridges and notch; imported editable BRep, without reconstructed parametric history |
| [Checks](evidence/FINAL_HULL_ARTIFACTS.json) | Exact file hashes and source PCB |

![Core mounting dimensions](preview/mounting.svg)

## Mounting

The PCB bottom stays at **Z = 10 mm**. Boss shape and **Ø2.1 mm blind printed pilots for M2.5 screws** are unchanged. These are prototype screw pilots, not heat-set insert seats. The pilot tool runs from Z4 to Z10.2 mm; the physical post ends at Z10 mm.

| Hole | Native KiCad X, Y (mm) | Hull X, Y (mm) |
|---|---|---|
| H1 — PCB GND fixing | 2, 0 | −76, 37 |
| H2 | 76, 0 | −2, 37 |
| H3 | 2, 71 | −76, −34 |
| H4 | 76, 71 | −2, −34 |

Transform: `hull_x = pcb_x − 78`, `hull_y = 37 − pcb_y`, in millimetres. Native PCB outline: X = −2…80, Y = −4…75. See the [Core mounting drawing](../../electronics/moss-core-v0.7/MOUNTING.md). H1 is grounded on the PCB; the plastic hull does not provide an electrical ground connection.

The Orange Pi mounts, hub supports, centred Cytron support, motor interfaces, fan clips, battery bay and native shell thicknesses remain unchanged. Physical screw engagement and printed fit still need an assembly test.

## Source and rebuild

The current native R92 input in `reference/Hull_R92_native.smt` includes the 9 November electrical update: a keyed opening for the 20 mm round main switch and an 11 mm rear charging socket. Core, Orange Pi and hub mounting positions are unchanged.

The active recipe imports that native solid in Fusion, removes the obsolete module mounts and rebuilds the existing Core, hub and centred Cytron supports. It exports the editable F3D, STEP and high-quality STL. A bounded STEP trim repair and a local rim-vertex weld precede the five cable-tie bridges and rounded wire notch.

Install the Python dependencies in [requirements.txt](requirements.txt). With Fusion running and its local MCP API available:

```sh
python source/rebuild.py --fusion-endpoint http://127.0.0.1:27182/mcp
```

The endpoint port can change after Fusion restarts. `--resume-after-native-mesh` rebuilds only the ties and notch from the current checked base files. Intermediate files stay under `harness/assets/` and `harness/output/`; final files are copied to `cad/`, `stl/` and `preview/`.

[Native construction](evidence/FUSION_NATIVE_BUILD.json), [STEP check](evidence/FINAL_STEP_HEAL_QA.json), [mesh check](evidence/LOCAL_WELD_QA.json), [tie checks](evidence/hull_tie_variant_QA.json) and [notch checks](evidence/DIVIDER_WIRE_NOTCH_QA.json) describe the generated geometry. `source/build_mount_refresh.py` and the older STEP references are retained as historical inputs; they are not the active rebuild path. `MANIFEST.json` inventories the published files.

MOSS hardware designs follow [CC BY-NC-SA 4.0](../../../LICENSE-HARDWARE). Code remains Apache-2.0; documentation and media remain CC BY 4.0, as described in the repository [NOTICE](../../../NOTICE). Third-party notices retain their own terms.
