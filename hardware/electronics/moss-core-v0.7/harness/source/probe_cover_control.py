from pathlib import Path
import vtk,numpy as np,json
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
h=Path(__file__).resolve().parents[1];z=np.load(h/'assets/HARNESS_SCENE.npz');v=z['LID__Upper_cover_R9_vertices'];f=z['LID__Upper_cover_R9_faces'].astype(np.int64);p=vtk.vtkPoints();p.SetData(numpy_to_vtk(v,deep=True));cells=vtk.vtkCellArray();cells.SetData(numpy_to_vtkIdTypeArray(np.arange(len(f)+1,dtype=np.int64)*3,deep=True),numpy_to_vtkIdTypeArray(f.ravel(),deep=True));poly=vtk.vtkPolyData();poly.SetPoints(p);poly.SetPolys(cells);tree=vtk.vtkOBBTree();tree.SetDataSet(poly);tree.BuildLocator();out=[]
for x in[-136.84,-131.84,-129.08,-126.54,-124,-121.46,-118.92,-116.84,-111.84,-108,-104,-93,-87]:
 row={'X':x,'rays':[]}
 for y in[10,25,32,39.359,42,45,48,52,55,58]:
  pts=vtk.vtkPoints();ids=vtk.vtkIdList();tree.IntersectWithLine([x,y,45],[x,y,100],pts,ids);hits=sorted(pts.GetPoint(i)[2]for i in range(pts.GetNumberOfPoints()));row['rays'].append({'Y':y,'cover_Z_hits':hits})
 out.append(row)
(h/'output/COVER_CYTRON_SECTION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2),flush=True)
