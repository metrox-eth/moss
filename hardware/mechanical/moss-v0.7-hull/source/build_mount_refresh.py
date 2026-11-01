"""Move only the three Core floor bosses with exact local BRep Booleans.

The baseline hull already contains the approved native support cleanup. The
original R92 floor is excluded from every removal tool. No geometry smoothing is used. The print mesh is generated separately by
Fusion from the final solid. The editable native recipe is retained separately.
"""
from pathlib import Path
import argparse
import hashlib
import json
import cadquery as cq
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(s):
    b = s.BoundingBox()
    return [[b.xmin, b.ymin, b.zmin], [b.xmax, b.ymax, b.zmax]]


def boss(x, y, cfg):
    f = cfg['boss']
    cone = cq.Solid.makeCone(f['foot_radius'], f['post_radius'],
                            f['post_start_z']-f['bottom_z'], cq.Vector(x,y,f['bottom_z']))
    post = cq.Solid.makeCylinder(f['post_radius'], f['top_z']-f['post_start_z'],
                                cq.Vector(x,y,f['post_start_z']))
    pilot = cq.Solid.makeCylinder(f['pilot_radius'], f['pilot_height'],
                                 cq.Vector(x,y,f['pilot_bottom_z']))
    return cone.fuse(post).clean(), pilot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    cfg = json.loads((ROOT/'source/mechanical_parameters.json').read_text())
    old_cfg = json.loads((ROOT/'reference/mechanical_parameters_before.json').read_text())
    baseline_step = ROOT/'reference/Hull_Core_72x67.step'
    baseline_stl = ROOT/'reference/Hull_Core_72x67.stl'
    original_step = ROOT/'reference/Hull_R92_Repaired.step'
    assert sha(baseline_step) == '8c903c024a3806a8f9481183a198cb4b94cb77afaa72a6c3dcc743cd4bcc77b9'
    assert sha(baseline_stl) == '38518aa90aa65797da2d848e8855cfe08b0d1b81aa76e1a6cf4aa0a0316f7e43'
    report = {'status':'LOCAL_BREP_DIAGNOSTIC', 'sources':{str(p):sha(p) for p in
              [baseline_step, baseline_stl, original_step]}, 'old_centres':old_cfg['core_mount_xy'],
              'new_centres':cfg['core_mount_xy'], 'boss_dimensions':cfg['boss'],
              'pcb_sha256':cfg['mounting_refresh']['pcb_sha256'],
              'approach':'Subtract only material outside the original native R92 floor at three obsolete bosses; add identical new boss forms. Native Fusion print export follows separately.',
              'fusion_f3d_status':'Source recipe updated; no regenerated F3D claimed by this offline BRep export.'}
    print('Importing baseline and native reference', flush=True)
    hull = cq.importers.importStep(str(baseline_step)).val()
    original_import = cq.importers.importStep(str(original_step)).val()
    original = max(original_import.Solids(), key=lambda s:s.Volume())
    assert hull.isValid() and original.isValid()
    assert len(hull.Solids()) == 1
    assert np.allclose(bounds(hull),bounds(original),atol=.002)
    before = hull
    old_centres = {tuple(x) for x in old_cfg['core_mount_xy']}
    new_centres = {tuple(x) for x in cfg['core_mount_xy']}
    removals = []
    restores = []
    additions = []
    new_pilots = []
    report['removals'] = []
    report['additions'] = []
    for xy in sorted(old_centres-new_centres):
        tool, pilot = boss(*xy,old_cfg)
        native_pilot_floor = original.intersect(pilot)
        native_in_pilot = native_pilot_floor.Volume(1e-7)
        assert native_in_pilot <= pilot.Volume(1e-7)+.001, (xy,native_in_pilot)
        # The shallow original pilot removed a tiny sloping-floor lip. Restore
        # that original native material when retiring the old screw position.
        if native_in_pilot > 1e-6:
            assert hull.intersect(native_pilot_floor).Volume(1e-7) < .001
            restores.append(native_pilot_floor)
        extra = tool.cut(pilot).cut(original).clean()
        actual = hull.intersect(extra)
        assert extra.isValid() and actual.isValid()
        assert extra.Volume(1e-7)>50
        assert abs(actual.Volume(1e-7)-extra.Volume(1e-7))<.02
        removals.append(extra)
        report['removals'].append({'centre_mm':xy,'volume_mm3':extra.Volume(1e-7),
                                   'native_in_pilot_mm3':native_in_pilot,'bounds_mm':bounds(extra),
                                   'actual_overlap_mm3':actual.Volume(1e-7)})
        print('Verified removable boss',xy,flush=True)
    for xy in sorted(new_centres-old_centres):
        tool, pilot = boss(*xy,cfg)
        native_in_pilot = original.intersect(pilot).Volume(1e-7)
        assert native_in_pilot <= pilot.Volume(1e-7)+.001, (xy,native_in_pilot)
        additions.append(tool)
        new_pilots.append(pilot)
        report['additions'].append({'centre_mm':xy,'native_in_pilot_mm3':native_in_pilot,
                                    'bounds_mm':bounds(tool)})
    assert len(removals)==len(additions)==3
    report['baseline_bounds_mm']=bounds(hull)
    (ROOT/'evidence/LOCAL_BREP_DIAGNOSTIC.json').write_text(json.dumps(report,indent=2)+'\n')
    if not args.execute:
        print('Local source/material diagnostic passed; outputs not generated.',flush=True)
        return
    expected_delta=-sum(t.Volume(1e-7) for t in removals)+sum(t.Volume(1e-7) for t in restores)
    for tool in removals:
        hull=hull.cut(tool).clean()
        assert hull.isValid() and len(hull.Solids())==1
    for tool in restores:
        hull=hull.fuse(tool).clean()
        assert hull.isValid() and len(hull.Solids())==1
    for tool in additions:
        expected_delta+=tool.Volume(1e-7)-hull.intersect(tool).Volume(1e-7)
        hull=hull.fuse(tool).clean()
        assert hull.isValid() and len(hull.Solids())==1
    for tool in new_pilots:
        expected_delta-=hull.intersect(tool).Volume(1e-7)
        hull=hull.cut(tool).clean()
        assert hull.isValid() and len(hull.Solids())==1
    out_step=ROOT/'cad/Hull_MOSS_V07_Core_Stack.step'
    cq.exporters.export(hull,str(out_step))
    imported=cq.importers.importStep(str(out_step)).val()
    assert imported.isValid() and len(imported.Solids())==1 and len(imported.Shells())==3
    assert np.allclose(bounds(imported),bounds(before),atol=.002)
    actual_delta=imported.Volume(1e-7)-before.Volume(1e-7)
    assert abs(actual_delta-expected_delta)<1, (actual_delta,expected_delta)
    report.update({'status':'LOCAL_CORE_MOUNT_BREP_COMPLETE',
       'step':{'valid':imported.isValid(),'solids':len(imported.Solids()),'shells':len(imported.Shells()),
               'bounds_mm':bounds(imported),'volume_mm3':imported.Volume(1e-7)},
       'preservation':{'expected_local_volume_delta_mm3':expected_delta,
               'native_global_volume_delta_mm3':actual_delta,
               'volume_integration_residual_mm3':actual_delta-expected_delta,
               'native_floor_restored_at_old_pilots_mm3':sum(t.Volume(1e-7) for t in restores),
               'all_native_operations_bound_to_six_boss_footprints':True},
       'artifacts':{str(out_step.relative_to(ROOT)):{'sha256':sha(out_step),'bytes':out_step.stat().st_size}}})
    (ROOT/'evidence/LOCAL_CORE_MOUNT_BREP.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['artifacts'],indent=2),flush=True)


if __name__=='__main__':
    main()
