"""Targeted current cable/sleeve screen against illustrative cooler and closed lid."""
from pathlib import Path
import json,hashlib
import numpy as np,vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
from export_harness_step import hermite_geometry
H=Path(__file__).resolve().parents[1];raw=np.load(H/'assets/HARNESS_SCENE.npz');z={k:raw[k].copy()for k in raw.files};raw.close();source=H/'output/ROUTE_LENGTHS.json';routes=json.loads(source.read_text())['routes']
keep=[];obs={};groups={}
for label,predicate in [('Illustrative_cooler',lambda n:n.startswith('PI__Cooler_')),('Closed_upper_cover',lambda n:n.startswith('LID__Upper_cover'))]:
 vs=[];fs=[];off=0;names=[]
 for k in z:
  if not k.endswith('_vertices'):continue
  n=k[:-9]
  if not predicate(n):continue
  v=z[k];f=z[n+'_faces'];vs.append(v);fs.append(f+off);off+=len(v);names.append(n)
 assert vs,label
 v=np.vstack(vs);f=np.vstack(fs).astype(np.int64);pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(v,deep=True));cells=vtk.vtkCellArray();cells.SetData(numpy_to_vtkIdTypeArray(np.arange(len(f)+1,dtype=np.int64)*3,deep=True),numpy_to_vtkIdTypeArray(f.ravel(),deep=True));poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells);dist=vtk.vtkImplicitPolyDataDistance();dist.SetInput(poly);obs[label]=dist;keep.extend([pts,cells,poly,dist]);groups[label]={'meshes':names,'vertices':len(v),'triangles':len(f),'bounds_world_mm':[v.min(0).tolist(),v.max(0).tolist()]}
rows=[]
def screen(rid,kind,pts,radius,label,dist,mask=None):
 pts=np.asarray(pts);mask=np.ones(len(pts),bool)if mask is None else mask;vals=[(abs(float(dist.EvaluateFunction(p)))-radius,p.tolist(),int(i))for i,p in enumerate(pts)if mask[i]]
 if not vals:return
 q=min(vals,key=lambda v:v[0]);rows.append({'route':rid,'geometry':kind,'obstacle':label,'radius_mm':radius,'minimum_sampled_skin_clearance_mm':round(q[0],5),'closest_point_world_mm':q[1],'closest_sample':q[2],'samples_below_zero':sum(d[0]<0 for d in vals),'hit_points_world_mm':[d[1]for d in vals if d[0]<0]})
for r in routes:
 for label,dist in obs.items():
  for i,path in enumerate(r['individual_wire_points_mm']):
   pts=np.array(path);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];mask=np.ones(len(pts),bool)
   # No blanket end exclusions. STOP lid endpoint is reported first as well;
   # any native switch-hole coincidence must be examined, not removed by policy.
   screen(r['id'],f'wire_{i+1}',pts,r['wire_ods_mm'][i]/2,label,dist,mask)
  if r['sleeve']:
   pts=np.array(r['points_mm']);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];mask=(s>17)&(s<s[-1]-18)
   screen(r['id'],'modeled_sleeve_plus_braid',pts,r['sleeve_outer_diameter_mm']/2+.1,label,dist,mask)
  if r['id']=='H03':
   pts=hermite_geometry(r['power_branch_points_mm'])[3];s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];mask=(s>22)&(s<s[-1]-36)
   screen(r['id'],'four_bridge_outputs_sleeve',pts,2.75,label,dist,mask)
report={'status':'SAMPLED_TARGETED_COOLER_AND_CLOSED_LID_SCREEN','PCB_sha256':json.loads((H/'source/PCB_CONNECTOR_ANCHORS.json').read_text())['sha256'],'route_data_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_scene_sha256':hashlib.sha256((H/'assets/HARNESS_SCENE.npz').read_bytes()).hexdigest(),'groups':groups,'method':'Nearest triangle surface distance minus individual insulation radius / actual modeled sleeve outer radius+0.1mm braid, at approximately0.9mm path samples. Entire individual wires, no endpoint exclusions. Sleeves checked over their actual displayed sample spans. Absolute distance: surface-clearance screen, not containment or physical-fit certification.','cooler_scope':'Illustrative fin/body envelope only; real cooler shape not supplied. Overall16mm board+cooler height is the user measurement.','results':rows,'violations':[r for r in rows if r['samples_below_zero']]}
(H/'output/COOLER_LID_CLEARANCE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'group_bounds':groups,'violations':report['violations']},indent=2),flush=True)
