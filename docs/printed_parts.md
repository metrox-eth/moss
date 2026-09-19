# MOSS V0.3 — prototype printed-parts inventory

Updated: **19 September 2026**.

The builder reports that printing appears complete, with one track to reprint. This inventory reconciles the final delivered print plans: **111 pieces in the intended current print set**, plus **two camera brackets whose printing is not confirmed**. It is not an independent physical count. Quantities are assembly requirements, not the cumulative number of prints, failed attempts or spares.

`reported_printed` follows that overall build update; it does not mean every part has been fitted or load-tested. The corrected motor-bracket revision still needs identification on the bench. The 0.8 mm track remains a replacement task.

## Current print feedback

- Two TPU 95A tracks have been printed. The first track was reported to have good flexibility and floor grip.
- The track made with the 0.8 mm nozzle is too stiff and is scheduled for reprinting; completion is not yet reported.
- Preserve the successful 0.4 mm print profile as the reference. Record nozzle, extrusion width, walls, layer height, infill and material together; the two prints do not isolate nozzle diameter as the only cause.
- The prototype front cover remains unfinished around the offset arm plate. The complete-cover redesign is parked for the next hardware revision and is excluded below.

## Reconciled quantities

| Assembly | Printed pieces |
|---|---:|
| Body | 4 |
| Tracks | 2 |
| Side structure | 8 |
| Ventilation | 2 |
| Motor mounts | 2 |
| Wheels and rollers | 20 |
| Tensioners and bearing retainers | 12 |
| Drivetrain spacers | 32 |
| Gaskets | 3 |
| Interior supports | 8 |
| SO-101 arm | 8 |
| NormaCore gripper | 8 |
| Gripper pads | 2 |
| **Total in the print plan** | **111** |

This includes 2 drive wheels made from 4 halves, 2 idler wheels made from 4 halves, 6 road rollers made from 12 halves, 32 small drivetrain spacers and 4 cross spacers. Metal hubs, bearings, shaft collars, servo horns and fasteners are not printed parts.

## Detailed inventory

G/D and −1/+1 retain the CAD naming so parts can be matched to their source files. Colour is taken from the print plan unless directly reported; no exact spool brand is inferred. Source filenames identify workshop revisions and are not download links or approved public releases.

### Body

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `Carter_PETG_continu_-_revision_mecanique_R8.stl` | 1 | Black PETG | Standalone H2S chassis | reported_printed |
| `Trappe_inferieure_acces_moteurs_R8.stl` | 1 | Black PETG | Standalone hatch | reported_printed |
| `MOSS_bac_corrige.stl` | 1 | Blue PLA | Standalone H2S bin | reported_printed |
| `MOSS_capot_monobloc_H2S_R5.stl` | 1 | Blue PLA | Standalone H2S cover | reported_printed |

- R8 export reference; the precise revision of the physical hatch is not recorded.
- Keep the printed prototype cover. The unfinished front interface remains as-is; full-cover redesign is parked.

### Tracks

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `MOSS_chenille_TPU95A_P1S_R2.stl` | 2 | TPU 95A | Standalone P1S tracks | one_accepted_one_reprint_planned |

- Two tracks have been printed. The first was reported flexible with good grip; the track printed with a 0.8 mm nozzle is too stiff and will be reprinted. Replacement has not been reported complete.

### Side structure

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `R8_G_Entretoise_traverse_-40_R8.stl` | 1 | Black PETG | 01 — P1S 0.8 | reported_printed |
| `R8_G_Entretoise_traverse_40_R8.stl` | 1 | Black PETG | 01 — P1S 0.8 | reported_printed |
| `R8_G_Flanc_interieur_R8.stl` | 1 | Black PETG | 01 — P1S 0.8 | reported_printed |
| `R8_D_Entretoise_traverse_-40_R8.stl` | 1 | Black PETG | 01 — P1S 0.8 | reported_printed |
| `R8_D_Entretoise_traverse_40_R8.stl` | 1 | Black PETG | 01 — P1S 0.8 | reported_printed |
| `R8_D_Flanc_interieur_R8.stl` | 1 | Black PETG | 01 — P1S 0.8 | reported_printed |
| `R8_G_Flanc_exterieur_R8.stl` | 1 | Black PETG | 02 — P1S 0.8 | reported_printed |
| `R8_D_Flanc_exterieur_R8.stl` | 1 | Black PETG | 03 — P1S 0.8 | reported_printed |

### Ventilation

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `Entree_air_sous_carter_-_chicane_demontable_R8.stl` | 1 | Black PETG | 03 — P1S 0.8 | reported_printed |
| `Extraction_air_sous_carter_-_chicane_demontable_R8.stl` | 1 | Black PETG | 03 — P1S 0.8 | reported_printed |

### Motor mounts

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `MOSS_support_moteur_G_V2_01.stl` | 1 | Black PETG | Standalone correction — P1S 0.4 | physical_revision_to_confirm |
| `MOSS_support_moteur_D_V2_01.stl` | 1 | Black PETG | Standalone correction — P1S 0.4 | physical_revision_to_confirm |

- Replaces the original plate-02 bracket; count once in the current build. Confirm the physical part is the corrected Ø31 mm M3 pattern, not the original bracket. Fit is not yet individually signed off.

### Wheels and rollers

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `R8_D_Roue_tendeuse_22d_demi-exterieure_R8.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_D_Roue_tendeuse_22d_demi-interieure_R8.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Roue_tendeuse_22d_demi-exterieure_R8.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Roue_tendeuse_22d_demi-interieure_R8.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8H_D_Roue_motrice_HEX12_demi_exterieure.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8H_D_Roue_motrice_HEX12_demi_interieure.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8H_G_Roue_motrice_HEX12_demi_exterieure.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8H_G_Roue_motrice_HEX12_demi_interieure.stl` | 1 | Black PETG | 04A — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_D_Galet625_-70_demi-exterieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_D_Galet625_-70_demi-interieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_D_Galet625_0_demi-exterieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_D_Galet625_0_demi-interieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_D_Galet625_70_demi-exterieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_D_Galet625_70_demi-interieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Galet625_-70_demi-exterieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Galet625_-70_demi-interieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Galet625_0_demi-exterieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Galet625_0_demi-interieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Galet625_70_demi-exterieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |
| `R8_G_Galet625_70_demi-interieure_R8.stl` | 1 | Black PETG | 04B — P1S 0.4; replaces 04 H2S | reported_printed |

### Tensioners and bearing retainers

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `R8_D_Couvercle_tendeur_exterieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_D_Couvercle_tendeur_interieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_G_Couvercle_tendeur_exterieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_G_Couvercle_tendeur_interieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_D_Coulisseau_exterieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_D_Coulisseau_interieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_G_Coulisseau_exterieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_G_Coulisseau_interieur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_D_Couvercle_palier_moteur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `R8_G_Couvercle_palier_moteur_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `Retenue_interieure_roulement_-1_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |
| `Retenue_interieure_roulement_1_R8.stl` | 1 | Black PETG | 05 — H2S 0.4 | reported_printed |

### Drivetrain spacers

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `R8_D_Entretoise_galet_-70_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_-70_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_-70_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_0_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_0_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_0_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_70_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_70_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_galet_70_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_tendeur_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_tendeur_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_tendeur_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_tendeur_retenue_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_tendeur_retenue_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_-70_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_-70_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_-70_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_0_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_0_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_0_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_70_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_70_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_galet_70_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_tendeur_centrale_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_tendeur_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_tendeur_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_tendeur_retenue_externe_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_tendeur_retenue_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_D_Entretoise_motrice_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8_G_Entretoise_motrice_interne_R8.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8H_D_Entretoise_motrice_externe_HEX12_L15_6.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |
| `R8H_G_Entretoise_motrice_externe_HEX12_L15_6.stl` | 1 | Black PETG | 06 — P1S 0.4; replaces 06 H2S | reported_printed |

### Gaskets

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `Joint_trappe_moteurs_R8.stl` | 1 | TPU 95A | 07 joints — H2S 0.4 | reported_printed |
| `Joint_sous_platine_-_appui_continu_R8.stl` | 1 | TPU 95A | 07 joints — H2S 0.4 | reported_printed |
| `R8_CAMERA_Joint_facade_D455_R8.stl` | 1 | TPU 95A | 07 joints — H2S 0.4 | reported_printed |

- R8 gasket source; fit to assembled interfaces remains to be checked.

### Interior supports

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `Berceau_electronique_R11.stl` | 1 | Black PLA | 07A_berceau_PLA_noir | reported_printed |
| `Support_porte_fusible_R9.stl` | 1 | Black PLA | 07A_berceau_PLA_noir | reported_printed |
| `Platine_bras_R11.stl` | 1 | Black PLA | 07B_platine_PLA_noir | reported_printed |
| `Retenue_socle_Jetson_R11.stl` | 4 | Black PLA | 07B_platine_PLA_noir | reported_printed |
| `Plateau_Jetson_R11.stl` | 1 | Black PLA | 07C_Jetson_PLA_noir | reported_printed |

- Replacement arm plate, not an additional plate stacked on top of R8/R9.

### SO-101 arm

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `SO101_Bras_superieur_clip.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_01 | reported_printed |
| `SO101_Avant_bras_clip.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_01 | reported_printed |
| `SO101_Base.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_01 | reported_printed |
| `SO101_Rotation_epaule.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_01 | reported_printed |
| `SO101_Support_epaule_clip.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_01 | reported_printed |
| `SO101_Base_motor_holder.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_02 | reported_printed |
| `SO101_Poignet_clip.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_02 | reported_printed |
| `SO101_Support_poignet.stl` | 1 | PLA — salmon in print plan | 08_bras_PLA_saumon_02 | reported_printed |

- Four cable clips are integrated into arm parts; no additional printed clip count.

### NormaCore gripper

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `Corps_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |
| `Machoire_gauche_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |
| `Machoire_droite_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |
| `Support_camera_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |
| `Flasque_1_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |
| `Flasque_2_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |
| `Pignon_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |
| `Guide_cable_NC90.stl` | 1 | PLA — turquoise in print plan | 09_pince_PLA_turquoise | reported_printed |

### Gripper pads

| Part / source STL | Qty | Material | Plate / job | Status |
|---|---:|---|---|---|
| `Patin_TPU_gauche.stl` | 1 | TPU 95A | 10_patins_TPU95A | reported_printed |
| `Patin_TPU_droit.stl` | 1 | TPU 95A | 10_patins_TPU95A | reported_printed |

## Parts to locate before calling the set complete

| Part | Qty | Source | Status |
|---|---:|---|---|
| D455 camera mounting bracket -1 | 1 | `R8_CAMERA_Equerre_D455_-1_R8.stl` | Printing not confirmed; no final plate located |
| D455 camera mounting bracket 1 | 1 | `R8_CAMERA_Equerre_D455_1_R8.stl` | Printing not confirmed; no final plate located |

## Superseded or excluded

- Original R8 motor brackets from plate 02: replaced by V2-01. Do not count both pairs as current parts.
- Original drive-wheel interfaces: use R8H HEX12 wheel halves and the corresponding external 15.6 mm spacers. The motor-to-shaft couplings are separate metal hardware.
- H2S wheel plate 04: superseded by P1S plates 04A and 04B. H2S spacer plate 06: superseded by P1S plate 06.
- Old R8/R9 arm plate and Jetson support: use the R11 print set; four Jetson-base retainers are included.
- The four arm cable clips are integrated into SO-101 printed pieces. Servo horns and idler horns are hardware supplied with the servos.
- The standard SO-101 gripper is replaced by the NC90 parallel gripper; do not count both.
- XT60 front extension, rejected cover extensions, parked complete-cover study, fit coupons and demonstration cable geometry are excluded.
- No dedicated battery cradle is in the final printed set.

## Naming and release status

The builder confirms that the **current physical prototype is V0.3**. Update the repository references that still call it V0.1 or describe V0.3 as a future release. R8, R8H, R10, R11 and V2-01 inside filenames are historical component identifiers; retain them for traceability and do not treat them as the current robot version. The next hardware revision is not assigned a new number here. A successful print and an assembled, validated part are separate milestones.

## Source records

- `MOSS_lots_impression_20260917/MANIFESTE.json` and plate-02/03 contents.
- `MOSS_suite_fabrication_20260917/*/Contenu.md` for wheels, tensioners, spacers and gaskets.
- `MOSS_P1S_04_PETG_noir/LIRE.md` and `LIRE_06.md` for replacement P1S plates.
- `MOSS_PLA_suite_20260918/plaques.json` for interior supports, arm, gripper and pads.
- `MOSS_supports_moteurs_V2_01/LIRE_AVANT_MONTAGE.md` for the corrected bracket pair.
- Latest builder report on completion and track stiffness.

The accompanying [machine-readable inventory](printed_parts.json) carries the same quantities and status distinctions.
