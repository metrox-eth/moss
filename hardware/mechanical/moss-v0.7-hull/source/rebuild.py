"""Regenerate the current 74x71 hull, then its five ties and battery-wire notch."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import argparse
import shutil

ROOT=Path(__file__).resolve().parents[1]


def run(path,*args):
    subprocess.run([sys.executable,str(path),*args],check=True,cwd=ROOT)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fusion-endpoint',default='http://127.0.0.1:27182/mcp')
    parser.add_argument('--resume-after-native-mesh',action='store_true')
    args=parser.parse_args()
    if not args.resume_after_native_mesh:
        run(ROOT/'source/build_mount_refresh.py','--execute')
        run(ROOT/'source/run_fusion_native_export.py','--endpoint',args.fusion_endpoint)
        run(ROOT/'source/weld_native_mesh.py')
    geometry_names=['cad/Hull_MOSS_V07_Core_Stack.step','stl/Hull_MOSS_V07_Print.stl',
                    'cad/Hull_MOSS_V07_Core_74x71_EDITABLE.f3d']
    geometry={'files':{n:{'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),
                          'bytes':(ROOT/n).stat().st_size} for n in geometry_names}}
    (ROOT/'evidence/GEOMETRY_SNAPSHOT.json').write_text(json.dumps(geometry,indent=2)+'\n')
    run(ROOT/'harness/source/build_hull_tie_variant.py')
    assets=ROOT/'harness/assets'
    names=['Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.step',
           'Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.stl','hull_tie_variant_QA.json']
    snapshot={'files':{n:{'sha256':hashlib.sha256((assets/n).read_bytes()).hexdigest(),
                         'bytes':(assets/n).stat().st_size} for n in names}}
    (assets/'PRE_NOTCH_SNAPSHOT.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    run(ROOT/'harness/source/add_divider_wire_notch.py')
    (ROOT/'preview').mkdir(exist_ok=True)
    for name,folder in [('Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.step','cad'),
                        ('Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.stl','stl'),
                        ('HULL_WITH_TIES_AND_NOTCH.npz','preview')]:
        shutil.copy2(assets/name,ROOT/folder/name)
    run(ROOT/'source/build_manifest.py')


if __name__=='__main__':
    main()
