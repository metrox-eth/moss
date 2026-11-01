"""Audit every native track direction, including fine-pitch and internal routes."""
from pathlib import Path
import argparse, collections, hashlib, json, re

def children(text):
    depth=0;quoted=False;escaped=False;start=None
    for i,c in enumerate(text):
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
            continue
        if c=='"':quoted=True
        elif c=='(':
            depth+=1
            if depth==2:start=i
        elif c==')':
            if depth==2 and start is not None:yield text[start:i+1]
            depth-=1
    assert depth==0 and not quoted

def audit(path):
    text=path.read_text();counts=collections.Counter();bad=[];arcs=[]
    for c in children(text):
        if c.startswith('(arc '):arcs.append(c)
        if not c.startswith('(segment'):continue
        def pos(key):
            return tuple(round(float(x)*1e6)for x in re.search(r'\('+key+r'\s+([\d.eE+-]+)\s+([\d.eE+-]+)\)',c).groups())
        a,z=pos('start'),pos('end');dx,dy=abs(z[0]-a[0]),abs(z[1]-a[1])
        layer=re.search(r'\(layer\s+"([^"]+)"',c)[1];counts[layer]+=1
        if min(dx,dy,abs(dx-dy))>2:bad.append(c)
    return {'pcb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'segments':sum(counts.values()),'segments_per_layer':dict(counts),'off_angle_segments':len(bad),'copper_arcs':len(arcs),'tolerance_native_IU_nm':2,'scope':'Every native segment, with no net, length or layer exception. Legal axes: horizontal, vertical and both 45-degree diagonals.','status':'PASS' if not bad and not arcs else 'FAIL'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('pcb',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=audit(a.pcb)
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='PASS' else 1)
