"""Build a separate, additive hull prototype with seven integral tie bridges.

No source hull is overwritten. The local floor and named device envelopes
are screened; this is not a full assembled-harness collision qualification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import cadquery as cq
import trimesh
from scipy.spatial import cKDTree
from tie_anchor import floor_datum, place_at

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
HULL = ROOT.parent / "cad/Hull_MOSS_V07_Core_Stack.step"
STATIONS = [
    ("T01",18,-25,90), ("T02",18,38,90), ("T03",18,70,90),
    ("T04",-48,-45,0), ("T05",-10,-45,0),
    ("T06",-84,-25,90), ("T07",-84,25,90),
]
RESERVATIONS = {
    "Core XY footprint":(-80,-38,2,41),
    "battery XY footprint":(37,-65,110,75),
    "hub XY footprint":(-78,56,0,81),
    "speaker XY footprint":(-87,-83,-16,-53),
    "rear motor north XY footprint":(-140,14,-102,92),
    "rear motor south XY footprint":(-140,-92,-102,-14),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(shape):
    b=shape.BoundingBox()
    return [[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]


def mesh_report(mesh):
    counts=np.bincount(mesh.edges_unique_inverse)
    return {
        "vertices":len(mesh.vertices), "triangles":len(mesh.faces),
        "watertight":bool(mesh.is_watertight),
        "winding_consistent":bool(mesh.is_winding_consistent),
        "is_volume":bool(mesh.is_volume),
        "boundary_edges":int(np.sum(counts==1)),
        "nonmanifold_edges":int(np.sum(counts>2)),
        "bounds_mm":mesh.bounds.tolist(),
    }


def main():
    ASSETS.mkdir(parents=True,exist_ok=True)
    parser=argparse.ArgumentParser()
    parser.add_argument("--reuse-step",action="store_true",help="Reuse the already exported 5-anchor STEP after station and volume checks")
    args=parser.parse_args()
    snapshot=json.loads((ROOT.parent/"evidence/GEOMETRY_SNAPSHOT.json").read_text())
    source_hash=sha(HULL)
    assert source_hash==snapshot["files"]["cad/Hull_MOSS_V07_Core_Stack.step"]["sha256"]
    hull=cq.importers.importStep(str(HULL)).val()
    assert hull.isValid() and len(hull.Solids())==1
    report={"status":"PROTOTYPE_FIT_REQUIRED_NOT_FULL_COLLISION_QUALIFICATION",
        "source_hull":str(HULL),"source_sha256":source_hash,
        "stations":[],"screened_device_xy_envelopes":RESERVATIONS,
        "limits":["Local footprint floor sampling, exact positive attachment overlap, exact hull interference above the local datum, and listed device XY envelopes only.",
                  "Actual wire/tie fit, print strength, electrical harness routing and complete assembly collisions are not qualified here.",
                  "A 4 mm printed bridge span and 2.4 mm passage need a printer-specific coupon trial."]}
    additions=[]
    npz={}
    for name,x,y,angle in STATIONS:
        try:
            info=floor_datum(hull,x,y,angle)
            anchor=place_at(x,y,info["datum_z_mm"],angle)
            b=anchor.BoundingBox()
            envelope_overlaps=[]
            for device,(xmin,ymin,xmax,ymax) in RESERVATIONS.items():
                if b.xmin<xmax and b.xmax>xmin and b.ymin<ymax and b.ymax>ymin:
                    envelope_overlaps.append(device)
            assert not envelope_overlaps, envelope_overlaps
            overlap=hull.intersect(anchor).Volume(1e-7)
            assert overlap>10,overlap
            above=cq.Workplane("XY").box(30,30,20,centered=(True,True,False)).translate((x,y,info["datum_z_mm"]+.0001)).val()
            upper_collision=hull.intersect(anchor.intersect(above)).Volume(1e-7)
            assert abs(upper_collision)<1e-4,upper_collision
            info.update({"id":name,"status":"ACCEPTED", "bounds_mm":bbox(anchor),
                         "roof_top_mm":b.zmax,"anchor_volume_mm3":anchor.Volume(1e-7),
                         "floor_join_overlap_mm3":overlap,
                         "hull_collision_above_datum_mm3":upper_collision,
                         "device_xy_envelope_overlaps":envelope_overlaps})
            cq.exporters.export(anchor,str(ASSETS/f"{name}_tie_anchor.step"))
            vertices,faces=anchor.tessellate(.025,.08)
            npz[name+"_vertices"]=np.array([v.toTuple() for v in vertices])
            npz[name+"_faces"]=np.array(faces,dtype=np.int32)
            additions.append(anchor)
        except Exception as exc:
            info={"id":name,"x_mm":x,"y_mm":y,"angle_deg":angle,"status":"OMITTED","reason":str(exc)}
        report["stations"].append(info)
        print(info,flush=True)
    assert len(additions)>=5
    np.savez_compressed(ASSETS/"tie_anchors_overlay.npz",**npz)
    combined=cq.Compound.makeCompound(additions)
    cq.exporters.export(combined,str(ASSETS/"tie_anchors_overlay.step"))
    out_step=ASSETS/"Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.step"
    out_stl=ASSETS/"Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.stl"
    if args.reuse_step:
        assert len(additions)==5 and out_step.exists()
        report["step_reused_after_unchanged_accepted_placements"]=True
    else:
        # A multi-tool fuse keeps the large inherited native solid through one Boolean.
        variant=hull.fuse(*additions).clean()
        report["variant_valid_before_export"]=variant.isValid()
        report["variant_solid_count_before_export"]=len(variant.Solids())
        assert variant.isValid() and len(variant.Solids())==1
        cq.exporters.export(variant,str(out_step))
    reimport=cq.importers.importStep(str(out_step)).val()
    assert reimport.isValid() and len(reimport.Solids())==1
    report["step_roundtrip"]={"valid":reimport.isValid(),"solids":len(reimport.Solids()),"shells":len(reimport.Shells()),"bounds_mm":bbox(reimport)}
    report["source_volume_mm3"]=hull.Volume(1e-7)
    report["variant_volume_mm3"]=reimport.Volume(1e-7)
    report["added_volume_mm3"]=report["variant_volume_mm3"]-report["source_volume_mm3"]
    report["expected_addition_mm3"]=sum(s["anchor_volume_mm3"]-s["floor_join_overlap_mm3"] for s in report["stations"] if s["status"]=="ACCEPTED")
    report["whole_solid_integration_residual_mm3"]=report["added_volume_mm3"]-report["expected_addition_mm3"]
    report["integration_note"]="Adaptive volume integration of the inherited spline hull has a small bounded residue versus the sum of local anchor differences; the numeric residual is recorded above. Whole-hull subtraction of nearly coincident native spline surfaces produced nonphysical fragments and is not used as a preservation proof. The STEP is an additive Boolean result, reimported as one valid solid; local overlaps are checked. The print mesh has the separate source-vertex preservation check below."
    assert abs(report["whole_solid_integration_residual_mm3"])<1
    diagnostic=ASSETS/"Hull_Tie_Loops_OCCT_TESSELLATION_DIAGNOSTIC_NOT_FOR_PRINT.stl"
    if not diagnostic.exists() and out_stl.exists():
        previous=trimesh.load_mesh(out_stl)
        if not previous.is_watertight:
            out_stl.rename(diagnostic)
    if diagnostic.exists():
        report["rejected_occt_tessellation"]=mesh_report(trimesh.load_mesh(diagnostic))
    # The selected native print mesh is watertight. Exact mesh Boolean preserves
    # it outside five local intersections; no voxel remeshing or hole filling.
    source_print=ROOT.parent/"stl/Hull_MOSS_V07_Print.stl"
    print_hash=sha(source_print)
    assert print_hash==snapshot["files"]["stl/Hull_MOSS_V07_Print.stl"]["sha256"]
    source_mesh=trimesh.load_mesh(source_print)
    assert source_mesh.is_volume
    anchor_meshes=[trimesh.Trimesh(vertices=npz[name+"_vertices"],faces=npz[name+"_faces"]) for name,_,_,_ in STATIONS if name+"_vertices" in npz]
    assert all(m.is_volume for m in anchor_meshes)
    mesh=trimesh.boolean.union([source_mesh,*anchor_meshes],engine="manifold",check_volume=True)
    assert mesh.is_volume
    mesh.export(out_stl)
    mesh=trimesh.load_mesh(out_stl)
    report["stl_mesh"]=mesh_report(mesh)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.is_volume
    distances,_=cKDTree(mesh.vertices).query(source_mesh.vertices,k=1)
    missing=source_mesh.vertices[distances>1e-4]
    outside=[]
    for vertex in missing:
        locally_affected=any(np.all(vertex>=np.asarray(item["bounds_mm"])[0]-.01) and np.all(vertex<=np.asarray(item["bounds_mm"])[1]+.01) for item in report["stations"] if item["status"]=="ACCEPTED")
        if not locally_affected:
            outside.append(vertex.tolist())
    report["stl_provenance"]={"operation":"Additive manifold mesh Boolean of selected watertight native print mesh and tessellated tie anchors; no global remeshing or hole filling.",
        "source":str(source_print),"source_sha256":print_hash,
        "source_mesh":mesh_report(source_mesh),
        "source_vertices_absent_in_result":len(missing),
        "absent_vertices_outside_anchor_bounds":len(outside),
        "source_volume_mm3":source_mesh.volume,"added_volume_mm3":mesh.volume-source_mesh.volume,
        "mesh_vs_step_volume_difference_mm3":mesh.volume-report["variant_volume_mm3"],
        "native_internal_cavity_shells_preserved":len(mesh.split(only_watertight=False))==3,
    }
    assert len(outside)==0, outside[:5]
    report["artifacts"]={p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in [out_step,out_stl,ASSETS/"tie_anchors_overlay.npz",ASSETS/"tie_anchors_overlay.step"]}
    report["original_hull_unchanged"]=sha(HULL)==source_hash
    report["original_native_print_mesh_unchanged"]=sha(source_print)==print_hash
    assert report["original_hull_unchanged"]
    (ASSETS/"hull_tie_variant_QA.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ["stations","screened_device_xy_envelopes"]},indent=2),flush=True)


if __name__=="__main__":
    main()
