from pathlib import Path
import cadquery as cq,json,hashlib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
from OCP.ShapeFix import ShapeFix_Solid
P=Path(__file__).parent.parent;src=P/'cad/Hull_MOSS_V07_NATIVE_MATCHED.step';s=cq.importers.importStep(str(src)).val();bad=[]
for i,f in enumerate(s.Faces()):
 if not f.isValid():
  b=f.BoundingBox();bad.append((i,f));print('bad',i,f.Area(),len(f.Edges()),[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],flush=True)
assert len(bad)==1 and abs(bad[0][1].Area())<.1 and len(bad[0][1].Edges())==3
sew=BRepBuilderAPI_Sewing(.001,True,True,True,False)
for i,f in enumerate(s.Faces()):
 if i!=bad[0][0]:sew.Add(f.wrapped)
sew.Perform();sh=cq.Shape.cast(sew.SewedShape());assert len(sh.Shells())==3
maker=BRepBuilderAPI_MakeSolid()
for shell in sh.Shells():maker.Add(shell.wrapped)
solid=cq.Solid(maker.Solid());fix=ShapeFix_Solid(solid.wrapped);fix.Perform();out=cq.Shape.cast(fix.Solid())
assert out.isValid() and len(out.Solids())==1 and len(out.Shells())==3
new=P/'cad/Hull_MOSS_V07_Core_Stack.step';cq.exporters.export(out,str(new))
roundtrip=cq.importers.importStep(str(new)).val();assert roundtrip.isValid() and len(roundtrip.Solids())==1
r={'status':'VALID_NATIVE_STEP_WITH_BOUNDED_TOPOLOGY_REPAIR','source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'operation':'Remove sole invalid near-zero-area planar sliver and sew adjacent native surfaces at0.001mm. Preserve all3shells in ONEsolid, including2internalvoids. No global remeshing.','removed_face_index':bad[0][0],'removed_face_area_mm2':bad[0][1].Area(),'sewing_tolerance_mm':.001,'reimport_valid':roundtrip.isValid(),'solid_count':len(roundtrip.Solids()),'shell_count':len(roundtrip.Shells()),'adaptive_source_volume_mm3':s.Volume(1e-7),'adaptive_repaired_volume_mm3':roundtrip.Volume(1e-7),'sha256':hashlib.sha256(new.read_bytes()).hexdigest()}
r['volume_difference_mm3']=r['adaptive_repaired_volume_mm3']-r['adaptive_source_volume_mm3'];(P/'evidence/FINAL_STEP_HEAL_QA.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2),flush=True)
