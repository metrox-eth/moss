#!/usr/bin/env python3
"""Compare manufactured non-legend layers, ignoring creation timestamps only."""
from pathlib import Path
import argparse, hashlib, json, difflib, re

def sha(b): return hashlib.sha256(b).hexdigest()
def normalized(p):
    lines=p.read_text().splitlines()
    return '\n'.join(l for l in lines if not (
        l.startswith('%TF.CreationDate,') or l.startswith('; #@! TF.CreationDate,')
        or l.startswith('G04 Created by KiCad (PCBNEW ')
        or l.startswith('; DRILL file KiCad ')))+'\n'

def moved_independent_line_block(a,b):
    """Accept only one verbatim relocation of complete absolute line segments."""
    aa=a.splitlines();bb=b.splitlines()
    changes=[op for op in difflib.SequenceMatcher(None,aa,bb,autojunk=False).get_opcodes() if op[0]!='equal']
    if sorted(op[0] for op in changes)!=['delete','insert']:return None
    deleted=next(op for op in changes if op[0]=='delete');inserted=next(op for op in changes if op[0]=='insert')
    block=aa[deleted[1]:deleted[2]]
    if block!=bb[inserted[3]:inserted[4]] or len(block)<4:return None
    if not re.fullmatch(r'%TO\.N,[^*]+\*%',block[0]) or not re.fullmatch(r'D\d+\*',block[1]):return None
    pairs=block[2:]
    if len(pairs)%2:return None
    for i,line in enumerate(pairs):
        if not re.fullmatch(r'X-?\d+Y-?\d+D0'+('2' if i%2==0 else '1')+r'\*',line):return None
    def context(lines,index):
        prefix=lines[:index]
        def last(pattern):return next((l for l in reversed(prefix) if re.fullmatch(pattern,l)),None)
        return {'polarity':last(r'%LP[DC]\*%'),'interpolation':last(r'G0[123]\*'),
                'format':last(r'%FS.*\*%'),'region':last(r'G3[67]\*')}
    ca=context(aa,deleted[1]);cb=context(bb,inserted[3])
    if ca!=cb or ca['polarity']!='%LPD*%' or ca['interpolation']!='G01*':return None
    if ca['region']=='G36*' or not ca['format'].startswith('%FSLAX'):return None
    # The following net tag resets the only changed object attribute.
    if not aa[deleted[2]].startswith('%TO.N,') or not bb[inserted[4]].startswith('%TO.N,'):return None
    if aa[:deleted[1]]+aa[deleted[2]:]!=bb[:inserted[3]]+bb[inserted[4]:]:return None
    return {'net_attribute':block[0],'aperture':block[1],'complete_line_segments':len(pairs)//2,
            'block_sha256':sha(('\n'.join(block)+'\n').encode()),'context':ca,
            'reason':'One identical self-contained route block changed output order. All other non-timestamp content is identical.'}

a=argparse.ArgumentParser(description=__doc__)
a.add_argument('--baseline',type=Path,required=True)
a.add_argument('--candidate',type=Path,required=True)
a.add_argument('--output',type=Path,required=True)
x=a.parse_args()
protected={'.gtl','.gbl','.g1','.g2','.gts','.gbs','.gtp','.gbp','.gm1','.drl'}
old={p.name for p in x.baseline.iterdir() if p.suffix in protected}
new={p.name for p in x.candidate.iterdir() if p.suffix in protected}
assert old==new,(old-new,new-old)
rows=[]
for name in sorted(old):
    a=x.baseline/name;b=x.candidate/name
    na,nb=normalized(a),normalized(b)
    same=na==nb
    moved=None if same else moved_independent_line_block(na,nb)
    rows.append({'file':name,'baseline_sha256':sha(a.read_bytes()),'candidate_sha256':sha(b.read_bytes()),'non_timestamp_content_byte_identical':same,'geometry_and_aperture_operations_identical':same or moved is not None,'verified_route_block_relocation':moved})
job='MOSS_Core_V07_Prototype-job.gbrjob'
j1=json.loads((x.baseline/job).read_text());j2=json.loads((x.candidate/job).read_text())
for j in (j1,j2):j['Header'].pop('CreationDate',None)
report={'status':'PASS' if all(r['geometry_and_aperture_operations_identical'] for r in rows) and j1==j2 else 'FAIL',
        'protected_outputs':rows,'gerber_job_unchanged_except_timestamp':j1==j2,
        'scope':'Copper, solder mask, paste, outline, plated and non-plated drills and Gerber job compared; exporter creation timestamps ignored. One relocated self-contained block of complete absolute line segments may be accepted only with identical drawing state, exact block bytes and otherwise identical content; it is separately reported. Printed legend files intentionally differ. This does not constitute hardware qualification.'}
x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'protected_files':len(rows),'changed':[r['file']for r in rows if not r['geometry_and_aperture_operations_identical']]}))
raise SystemExit(0 if report['status']=='PASS' else 1)
