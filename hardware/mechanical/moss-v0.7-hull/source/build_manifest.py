"""Inventory published source inputs and current hull outputs without CAD imports."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'MANIFEST.json'}
GENERATED=('harness/assets/','harness/output/')


def main():
    files={}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(ROOT).as_posix()
        if rel in EXCLUDED or rel.startswith(GENERATED) or '__pycache__' in p.parts:continue
        if rel.endswith('.pyc'):continue
        files[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (ROOT/'MANIFEST.json').write_text(json.dumps({'status':'CURRENT_HULL_74x71_SOURCE_AND_EXPORT_INVENTORY',
            'units':'mm','pcb_sha256':'7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14',
            'files':files},indent=2)+'\n')


if __name__=='__main__':
    main()
