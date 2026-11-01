"""Sample current declared cable skins against supplied context triangle meshes.
No physical-fit certification; intentional terminal seating regions excluded only
for their own mating device. Nearest triangle distance, not vertex distances.
"""
from pathlib import Path
import json,hashlib
import numpy as np,vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
P=Path(__file__).resolve().parents[1];raw=np.load(P/'assets/HARNESS_SCENE.npz');z={k:raw[k].copy()for k in raw.files};raw.close();rr=json.loads((P/'output/ROUTE_LENGTHS.json').read_text())['routes'];functions={}
obstacles={
 'Hull':lambda n:n.startswith('HULL__'),
 'OrangePi':lambda n:n.startswith('PI__OrangePi_native_'),
 'Pi_standoffs':lambda n:n.startswith('PI__OrangePi_20mm_standoff_'),
 'Cytron':lambda n:n.startswith('CONTEXT__Cytron_'),
 'Speaker':lambda n:n=='CONTEXT__Speaker_R92_original',
 'Motors':lambda n:n.startswith('CONTEXT__Motor_')or n.startswith('CONTEXT__Drive_Motor_'),
}
keep=[]
for label,test in obstacles.items():
 vs=[];fs=[];offset=0
 for key in z:
  if not key.endswith('_vertices'):continue
  name=key[:-9]
  if not test(name):continue
  v=z[key];f=z[name+'_faces'];vs.append(v);fs.append(f+offset);offset+=len(v)
 if not vs:continue
 v=np.vstack(vs);f=np.vstack(fs).astype(np.int64);points=vtk.vtkPoints();points.SetData(numpy_to_vtk(v,deep=True));cells=vtk.vtkCellArray();cells.SetData(numpy_to_vtkIdTypeArray(np.arange(len(f)+1,dtype=np.int64)*3,deep=True),numpy_to_vtkIdTypeArray(f.ravel(),deep=True));poly=vtk.vtkPolyData();poly.SetPoints(points);poly.SetPolys(cells);dist=vtk.vtkImplicitPolyDataDistance();dist.SetInput(poly);functions[label]=dist;keep.extend([points,cells,poly,dist])
rows=[]
for r in rr:
 for obs,dist in functions.items():
  best=(1e9,None,None);violations=0
  for w,path in enumerate(r['individual_wire_points_mm']):
   pts=np.array(path);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];sel=np.ones(len(pts),bool)
   if (obs=='OrangePi'and r['id']in['U01','U03'])or(obs=='Speaker'and r['id']=='O02')or(obs=='Motors'and r['id']in['H04','H05'])or(obs=='Cytron'and r['id']in['H02','H03']):sel&=s<s[-1]-18
   rad=r['wire_ods_mm'][w]/2
   for i in np.flatnonzero(sel):
    d=abs(dist.EvaluateFunction(pts[i]))-rad
    if d<best[0]:best=(d,w+1,pts[i].tolist())
    if d<0:violations+=1
  rows.append({'route':r['id'],'obstacle':obs,'minimum_sampled_skin_clearance_mm':round(best[0],3),'closest_wire':best[1],'closest_point_world_mm':best[2],'samples_below_zero':violations})

  if r['sleeve']:
   pth=np.array(r['points_mm']);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pth,axis=0),axis=1))];sel=(ss>17)&(ss<ss[-1]-18)
   rad=r['sleeve_outer_diameter_mm']/2+.1
   vals=[(abs(dist.EvaluateFunction(pth[i]))-rad,pth[i].tolist())for i in np.flatnonzero(sel)]
   if vals:
    q=min(vals,key=lambda d:d[0]);rows.append({'route':r['id'],'obstacle':obs,'geometry':'MODELED_SLEEVE_PLUS_BRAID','minimum_sampled_skin_clearance_mm':round(q[0],3),'closest_point_world_mm':q[1],'samples_below_zero':sum(d[0]<0 for d in vals)})
# The four Cytron winding outputs also share a separate modeled sleeve.
from export_harness_step import hermite_geometry
h03=next(r for r in rr if r['id']=='H03');bp=hermite_geometry(h03['power_branch_points_mm'])[3];ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(bp,axis=0),axis=1))];sel=(ss>22)&(ss<ss[-1]-36)
for obs,dist in functions.items():
 vals=[(abs(dist.EvaluateFunction(bp[i]))-2.75,bp[i].tolist())for i in np.flatnonzero(sel)]
 if vals:
  q=min(vals,key=lambda d:d[0]);rows.append({'route':'H03','obstacle':obs,'geometry':'FOUR_BRIDGE_OUTPUTS_SLEEVE','minimum_sampled_skin_clearance_mm':round(q[0],3),'closest_point_world_mm':q[1],'samples_below_zero':sum(d[0]<0 for d in vals)})
report={'status':'SAMPLED_CABLE_CONTEXT_SCREEN','PCB_sha256':json.loads((P/'source/PCB_CONNECTOR_ANCHORS.json').read_text())['sha256'],'source_scene_sha256':hashlib.sha256((P/'assets/HARNESS_SCENE.npz').read_bytes()).hexdigest(),'route_lengths_sha256':hashlib.sha256((P/'output/ROUTE_LENGTHS.json').read_bytes()).hexdigest(),'method':'Nearest triangle surface distance minus conductor radius or modeled sleeve radius+0.1mm braid allowance at approx0.9mm intervals. Absolute distance only; no containment proof. Exclude final18mm only at the matching matingdevice for individual wires; no exclusion for modeled sleeve sample spans. Complete declared sleeve volumes vsPi checked separately in FULL_SLEEVE_OPI_QA.json. No physical tolerance/bend/electrical certification.','results':rows,'violations':[r for r in rows if r['samples_below_zero']]}
(P/'output/CURRENT_ROUTE_CLEARANCE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['violations'],indent=2),flush=True)
