#!/usr/bin/env python3
"""Optional regeneration of the included open-bin collision approximation.

Requires trimesh/coacd. The hull cap and requested concavity are approximation
settings, not a certified physical clearance or surface-error bound.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import trimesh
import coacd

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'model/manifest.json'
    manifest=json.loads(path.read_text())
    row=next(r for r in manifest['parts'] if r['name'].startswith('14_Bin'))
    mesh=trimesh.load(ROOT/'model'/row['file'],force='mesh')
    coacd.set_log_level('warn')
    pieces=coacd.run_coacd(coacd.Mesh(mesh.vertices,mesh.faces),threshold=.004,
        real_metric=True,max_convex_hull=48,resolution=2000,mcts_nodes=10,
        mcts_iterations=80,mcts_max_depth=3,max_ch_vertex=128,seed=0)
    files=[]
    for i,(vertices,faces) in enumerate(pieces):
        file=f'meshes/collision/bin_{i:03d}.stl'
        dst=ROOT/'model'/file;dst.parent.mkdir(exist_ok=True)
        trimesh.Trimesh(vertices,faces,process=False).export(dst)
        files.append(file)
    row['collision_files']=files
    row['collision_method']={'algorithm':'CoACD','requested_concavity_m':.004,
        'hull_cap':48,'hulls':len(files),'certified_error_bound':False}
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(row['collision_method']))


if __name__=='__main__':main()
