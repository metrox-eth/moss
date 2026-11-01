from pathlib import Path
import trimesh,numpy as np,json
from scipy.spatial import cKDTree
P=Path(__file__).parent.parent
m=trimesh.load_mesh(P/'stl/Hull_MOSS_V07_NATIVE_MATCHED.stl');c=np.bincount(m.edges_unique_inverse);be=m.edges_unique[c==1];bv=np.unique(be);v=m.vertices[bv]
pairs=list(cKDTree(v).query_pairs(.00002));assert len(pairs)==1,pairs
i,j=bv[pairs[0][0]],bv[pairs[0][1]];displacement=float(np.linalg.norm(m.vertices[i]-m.vertices[j]));f=m.faces.copy();f[f==j]=i
valid=(f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,2]!=f[:,0]);out=trimesh.Trimesh(vertices=m.vertices.copy(),faces=f[valid],process=False);out.remove_unreferenced_vertices();c=np.bincount(out.edges_unique_inverse)
r={'operation':'Merge only one pair of coincident boundary vertices along original rim; no global quantization, mesh simplification or filling.','target_vertex_indices':[int(i),int(j)],'maximum_displacement_mm':displacement,'removed_zero_area_degenerate_faces':int((~valid).sum()),'faces_before':len(m.faces),'faces_after':len(out.faces),'watertight':out.is_watertight,'winding_consistent':out.is_winding_consistent,'is_volume':out.is_volume,'boundary_edges':int((c==1).sum()),'nonmanifold_edges':int((c>2).sum()),'volume_mm3':out.volume,'volume_delta_mm3':out.volume-m.volume,'connected_shells':out.body_count}
(P/'evidence/LOCAL_WELD_QA.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2),flush=True)
assert out.is_watertight and out.is_volume and displacement<.00002
out.export(P/'stl/Hull_MOSS_V07_Print.stl')
