"""Read-only current native PCB anchor extraction, with explicit plug-exit assumptions."""
from pathlib import Path
import json,hashlib
import pcbnew,wx
app=wx.App(False); quiet=wx.LogNull()
P=Path(__file__).resolve().parents[1]; PCB=P.parent/'electrical/MOSS_Core_V07_Prototype.kicad_pcb'; PCB=PCB if PCB.is_file() else P.parent/'current_prototype/electrical/MOSS_Core_V07_Prototype.kicad_pcb'
b=pcbnew.LoadBoard(str(PCB)); refs=['J1','J2','J3','J4','J5','J7','J8','J10','J11','J14','J15','J20'];out={}
for fp in b.GetFootprints():
 ref=fp.GetReference()
 if ref not in refs: continue
 xy=fp.GetPosition(); pads=[]
 for p in fp.Pads():
  v=p.GetPosition(); pads.append({'pad':p.GetNumber(),'net':p.GetNetname(),'pcb_xy_mm':[pcbnew.ToMM(v.x),pcbnew.ToMM(v.y)],'world_xy_mm':[pcbnew.ToMM(v.x)-78,37-pcbnew.ToMM(v.y)]})
 out[ref]={'value':fp.GetValue(),'footprint':str(fp.GetFPID()),'pcb_xy_mm':[pcbnew.ToMM(xy.x),pcbnew.ToMM(xy.y)],'orientation_deg':fp.GetOrientationDegrees(),'world_origin_mm':[pcbnew.ToMM(xy.x)-78,37-pcbnew.ToMM(xy.y),11.595],'pads':pads}
assert set(out)==set(refs)
r={'board':'../current_prototype/electrical/MOSS_Core_V07_Prototype.kicad_pcb','sha256':hashlib.sha256(PCB.read_bytes()).hexdigest(),'frame':'native R92 mm; Core bottomZ10, component datum11.595','connectors':out,'scope':'Native pad positions/nets only; cable wire-exit planes are separate declared reservations in connector_visuals.py.'}
(P/'source/PCB_CONNECTOR_ANCHORS.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'sha256':r['sha256'],'connectors':{k:v['pcb_xy_mm'] for k,v in out.items()}},indent=2))
