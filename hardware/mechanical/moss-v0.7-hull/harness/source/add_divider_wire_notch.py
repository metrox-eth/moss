"""Add the approved R2-bottom, top-open wire notch to the five-anchor prototype.

All native hull files remain unchanged. Only the separate harness prototype
is replaced; its pre-notch exports are saved under assets/internal_history.
"""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import cadquery as cq
import trimesh
from scipy.spatial import cKDTree

P=Path(__file__).resolve().parents[1]
A=P/'assets'
O=P/'output'
# Each current pre-notch STEP owns a separate immutable history snapshot.
NAME='Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bb(shape):
    b=shape.BoundingBox()
    return [[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]


def mesh_report(m):
    counts=np.bincount(m.edges_unique_inverse)
    return {'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),
            'is_volume':bool(m.is_volume),'vertices':len(m.vertices),'triangles':len(m.faces),
            'boundary_edges':int(np.sum(counts==1)),'nonmanifold_edges':int(np.sum(counts>2)),
            'bounds_mm':m.bounds.tolist()}


def main():
    O.mkdir(parents=True,exist_ok=True)
    snapshot=json.loads((A/'PRE_NOTCH_SNAPSHOT.json').read_text())
    HISTORY=A/'internal_history'/('pre_notch_'+snapshot['files'][NAME+'.step']['sha256'][:16])
    HISTORY.mkdir(parents=True,exist_ok=True)
    for name in [NAME+'.step',NAME+'.stl','hull_tie_variant_QA.json']:
        if not (HISTORY/name).exists():
            shutil.copy2(A/name,HISTORY/name)
    src_step=HISTORY/(NAME+'.step')
    src_stl=HISTORY/(NAME+'.stl')
    assert sha(src_step)==snapshot['files'][NAME+'.step']['sha256']
    assert sha(src_stl)==snapshot['files'][NAME+'.stl']['sha256']
    native=P.parent/'cad/Hull_MOSS_V07_Core_Stack.step'
    native_print=P.parent/'stl/Hull_MOSS_V07_Print.stl'
    native_hashes={str(p):sha(p) for p in [native,native_print]}
    s=cq.importers.importStep(str(src_step)).val()
    cutter=cq.Workplane('XY').box(10,14,15.5,centered=(False,False,False)).translate((24,55,56.5)).edges('|X and <Z').fillet(2).val()
    removed=s.intersect(cutter)
    assert removed.isValid() and len(removed.Solids())==1
    rb=np.asarray(bb(removed))
    assert np.allclose(rb,[[26,55,56.5],[32,69,66]],atol=1e-5),rb
    result=s.cut(cutter).clean()
    assert result.isValid() and len(result.Solids())==1
    out_step=A/(NAME+'.step')
    out_stl=A/(NAME+'.stl')
    cq.exporters.export(result,str(out_step))
    reimport=cq.importers.importStep(str(out_step)).val()
    assert reimport.isValid() and len(reimport.Solids())==1
    # Mesh subtraction is performed on the previously accepted watertight mesh.
    baseline=trimesh.load_mesh(src_stl)
    vertices,faces=cutter.tessellate(.01,.05)
    cutter_mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vertices],faces=faces)
    assert baseline.is_volume and cutter_mesh.is_volume
    mesh=trimesh.boolean.difference([baseline,cutter_mesh],engine='manifold',check_volume=True)
    assert mesh.is_volume
    mesh.export(out_stl)
    mesh=trimesh.load_mesh(out_stl)
    assert mesh.is_volume
    distances,_=cKDTree(mesh.vertices).query(baseline.vertices,k=1)
    absent=baseline.vertices[distances>1e-4]
    outside=[v.tolist() for v in absent if not (np.all(v>=np.array([24,55,56.5])-.001) and np.all(v<=np.array([34,69,72])+.001))]
    assert not outside,outside[:5]
    np.savez_compressed(A/'HULL_WITH_TIES_AND_NOTCH.npz',Hull_V07_vertices=mesh.vertices,
                        Hull_V07_faces=mesh.faces,Hull_V07_color=np.array([.14,.165,.18]))
    cq.exporters.export(cutter,str(A/'divider_wire_notch_cut_tool.step'))
    notch={
        'status':'PROTOTYPE_FIT_REQUIRED_NOT_FULL_COLLISION_QUALIFICATION',
        'operation':'One top-open notch through the battery divider, subtractive only inside the verified local tool.',
        'tool_bounds_mm':[[24,55,56.5],[34,69,72]],
        'actual_removed_material_bounds_mm':rb.tolist(),
        'actual_removed_material_volume_mm3':removed.Volume(1e-7),
        'actual_removed_solid_count':len(removed.Solids()),
        'opening_width_mm':14,'maximum_depth_below_divider_top_mm':9.5,
        'bottom_corner_radius_mm':2,'additional_edge_fillet_mm':0,
        'edge_note':'The two lower profile corners are R2; no global edge fillet was applied to inherited native surfaces.',
        'baseline_step_sha256':sha(src_step),'baseline_stl_sha256':sha(src_stl),
        'step_roundtrip':{'valid':reimport.isValid(),'solid_count':len(reimport.Solids()),'shell_count':len(reimport.Shells()),'bounds_mm':bb(reimport)},
        'stl_mesh':mesh_report(mesh),
        'mesh_removed_volume_mm3':baseline.volume-mesh.volume,
        'pre_notch_vertices_absent_in_result':len(absent),
        'absent_vertices_outside_notch_tool':len(outside),
        'mesh_shell_count':len(mesh.split(only_watertight=False)),
        'internal_history':str(HISTORY),
        'native_source_hashes':native_hashes,
        'native_sources_unchanged':all(sha(Path(p))==v for p,v in native_hashes.items()),
        'harness_step_regenerated':False,
        'limits':['Local geometry opening only; wire clearance, actual insulation contact, cover fit and access remain for root routing checks and physical trial.'],
    }
    assert notch['native_sources_unchanged']
    for name in [NAME+'.step',NAME+'.stl']:
        shutil.copy2(A/name,O/name)
    qa=json.loads((HISTORY/'hull_tie_variant_QA.json').read_text())
    qa['divider_wire_notch']=notch
    qa['step_roundtrip']=notch['step_roundtrip']
    qa['stl_mesh']=notch['stl_mesh']
    qa['pre_notch_anchor_QA_is_preserved']=True
    qa['baseline_anchor_addition_volume_fields_scope']='The source_volume, variant_volume, added_volume, expected_addition and stl_provenance fields above describe the archived five-anchor baseline before subtracting the notch. Use divider_wire_notch for the local subtractive change.'
    qa['artifacts'].update({p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in [out_step,out_stl,A/'HULL_WITH_TIES_AND_NOTCH.npz']})
    for base in [A,O]:
        (base/'hull_tie_variant_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
        (base/'DIVIDER_WIRE_NOTCH_QA.json').write_text(json.dumps(notch,indent=2)+'\n')
    print(json.dumps(notch,indent=2),flush=True)


if __name__=='__main__':
    main()
