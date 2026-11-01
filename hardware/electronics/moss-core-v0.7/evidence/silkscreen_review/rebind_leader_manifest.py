"""Rebind only an external layout manifest after revalidating its consumed fields.

The previous full comparator result and its exact board hashes must still pass.
Every final declared leader is checked against the previous measured native
object. Other layout metadata is not used by the electrical-delta comparator.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,math

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--report',type=Path,required=True)
ap.add_argument('--baseline-board',type=Path,required=True)
ap.add_argument('--candidate-board',type=Path,required=True)
ap.add_argument('--manifest',type=Path,required=True)
args=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads(args.report.read_text());m=json.loads(args.manifest.read_text())
assert r['electrical_and_physical_equivalence_pass']and r['new_reference_style_pass']
assert sha(args.baseline_board)==r['baseline_board_sha256']==m['baseline_sha256']
assert sha(args.candidate_board)==r['candidate_board_sha256']==m['candidate_sha256']
old={x['uuid']:x for x in r['new_silk_leaders']['objects']};seen=set();checks=[]
normalize=lambda l:{'F.Silkscreen':'F.SilkS','B.Silkscreen':'B.SilkS'}.get(l,l)
tol=r['new_silk_leaders']['native_endpoint_tolerance_mm']
for leader in m['leaders']:
    points=leader['points_mm'];ids=leader['graphic_uuids']
    assert len(ids)==len(points)-1
    for i,uid in enumerate(ids):
        assert uid in old and uid not in seen;seen.add(uid);p=old[uid]
        assert p['reference']==leader['ref']and p['face']==normalize(leader['side'])
        assert math.isfinite(leader['width_mm'])and leader['width_mm']>=.15
        assert abs(p['width_mm']-leader['width_mm'])<=tol
        if p['coordinate_frame']=='footprint_local':assert leader['coordinate_frame']=='footprint_local'
        delta=max(abs(float(a)-float(b))for actual,expected in [(p['start_mm'],points[i]),(p['end_mm'],points[i+1])]for a,b in zip(actual,expected))
        assert delta<=tol
        checks.append({'uuid':uid,'reference':p['reference'],'native_object_sha256':p['native_object_sha256'],
                       'final_declared_geometry_matches_previous_native_measurement':True,'max_coordinate_delta_mm':delta})
assert seen==set(old),'Final whitelist differs from the previously measured native objects'
original=args.report.with_name('SILK_ONLY_EQUIVALENCE_ORIGINAL.json')
assert not original.exists(),'Original proof already saved; avoid accidental chained rebinding'
original.write_bytes(args.report.read_bytes())
proof={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_EXTERNAL_MANIFEST_METADATA_REBIND',
       'old_comparator_report_sha256':sha(original),'old_manifest_sha256':r['leader_manifest_sha256'],
       'new_manifest_sha256':sha(args.manifest),'baseline_board_sha256':r['baseline_board_sha256'],
       'candidate_board_sha256':r['candidate_board_sha256'],'consumed_manifest_dependencies':
       ['baseline_sha256','candidate_sha256','leaders.ref','leaders.side','leaders.width_mm',
        'leaders.points_mm','leaders.graphic_uuids','leaders.coordinate_frame if fp_line'],
       'all_consumed_dependencies_revalidated':True,'native_leaders':checks,
       'other_layout_metadata':'Not used by the protected-design comparator; this does not assert byte identity of unconsumed layout metadata. U15 locator metadata is separately bound by the final layout/locator evidence.',
       'full_comparator_reexecuted':False,'clearance_reexecuted':False,'electrical_simulation_reexecuted':False,
       'rebind_script_sha256':sha(Path(__file__))}
proof_path=args.report.with_name('LEADER_MANIFEST_REBIND.json')
proof_path.write_text(json.dumps(proof,indent=2)+'\n')
r['leader_manifest_sha256']=proof['new_manifest_sha256']
r['external_manifest_metadata_rebinding']={'proof_file':proof_path.name,'proof_sha256':sha(proof_path),
        'original_report_file':original.name,'original_report_sha256':sha(original),
        'full_comparator_reexecuted':False,'reason':'Unchanged exact PCB; final manifest dependencies are matched to the original measured native leader objects.'}
args.report.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'status':proof['status'],'new_manifest_sha256':proof['new_manifest_sha256'],
                  'all_consumed_dependencies_revalidated':True,'native_leader_segments':len(checks)},indent=2))
